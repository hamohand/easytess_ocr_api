"""
Service d'extraction de contenu PDF — Version améliorée
Extrait le texte et les tableaux directement depuis un fichier PDF
en utilisant pdfplumber avec plusieurs stratégies de détection.

Fonctionnalités:
  - Détection multi-stratégie des tableaux (standard, text, lines)
  - Gestion des cellules fusionnées
  - Métadonnées de tableaux (dimensions, en-têtes)
  - Extraction du texte hors-tableaux
  - Statistiques par page et globales
"""
import pdfplumber
import logging
import re

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# Stratégies de détection de tableaux
# ──────────────────────────────────────────────────────────
TABLE_STRATEGIES = {
    "standard": {
        # Détection par défaut — lignes visibles
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 5,
        "join_tolerance": 5,
        "edge_min_length": 10,
        "min_words_vertical": 3,
        "min_words_horizontal": 3,
    },
    "text": {
        # Détection par alignement de texte (tableaux sans bordures)
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 8,
        "join_tolerance": 8,
        "edge_min_length": 5,
        "min_words_vertical": 2,
        "min_words_horizontal": 2,
        "text_x_tolerance": 5,
        "text_y_tolerance": 5,
    },
    "lines_strict": {
        # Détection stricte — uniquement les lignes bien tracées
        "vertical_strategy": "lines_strict",
        "horizontal_strategy": "lines_strict",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 15,
    },
}


def _clean_cell(value):
    """Nettoie une valeur de cellule."""
    if value is None:
        return ""
    return str(value).strip().replace('\n', ' ')


def _detect_header_row(rows):
    """
    Tente de détecter si la première ligne est un en-tête.
    Heuristique : si les cellules de la 1ère ligne sont toutes
    non-numériques et non-vides, c'est probablement un en-tête.
    """
    if not rows or len(rows) < 2:
        return False

    first_row = rows[0]
    if not first_row:
        return False

    non_empty = [c for c in first_row if c and str(c).strip()]
    if len(non_empty) == 0:
        return False

    # Si aucune cellule n'est purement numérique → probablement un en-tête
    numeric_pattern = re.compile(r'^[\d\s.,€$%]+$')
    return not any(numeric_pattern.match(str(c).strip()) for c in non_empty if c)


def _extract_table_data(table, table_counter, page_num, table_columns=None):
    """
    Extrait les données d'un tableau pdfplumber avec métadonnées.

    Returns:
        dict: bloc tableau structuré ou None si vide
    """
    raw_rows = table.extract()
    if not raw_rows:
        return None

    has_header = _detect_header_row(raw_rows)
    nb_cols_detected = max(len(row) for row in raw_rows) if raw_rows else 0
    headers_list = None

    lignes = []
    for row_idx, row in enumerate(raw_rows):
        cols = table_columns if table_columns else list(range(len(row)))

        row_data = {}
        for col_idx in cols:
            if 0 <= col_idx < len(row):
                cell_value = _clean_cell(row[col_idx])

                # Si on a détecté un en-tête et c'est la 1ère ligne,
                # utiliser les noms comme clés
                if has_header and row_idx == 0:
                    if headers_list is None:
                        headers_list = []
                    headers_list.append(cell_value if cell_value else f"col_{col_idx:02d}")
                    continue

                # Utiliser le nom d'en-tête si disponible
                if headers_list and col_idx < len(headers_list):
                    key = headers_list[col_idx]
                else:
                    key = f"col_{col_idx:02d}"

                row_data[key] = cell_value

        if row_data:
            lignes.append(row_data)

    if not lignes:
        return None

    result = {
        "type": "tableau",
        "numero": table_counter,
        "page": page_num,
        "lignes": lignes,
        "metadata": {
            "nb_lignes": len(lignes),
            "nb_colonnes": nb_cols_detected,
            "a_entete": has_header,
        }
    }

    if headers_list:
        result["metadata"]["entetes"] = headers_list

    # Bounding box du tableau
    if hasattr(table, 'bbox') and table.bbox:
        result["metadata"]["bbox"] = {
            "x0": round(table.bbox[0], 2),
            "y0": round(table.bbox[1], 2),
            "x1": round(table.bbox[2], 2),
            "y1": round(table.bbox[3], 2),
        }

    return result


def _try_extract_tables(page, strategy_name="standard"):
    """
    Tente d'extraire des tableaux avec une stratégie donnée.

    Returns:
        list: tables trouvées (peut être vide)
    """
    settings = TABLE_STRATEGIES.get(strategy_name, TABLE_STRATEGIES["standard"])
    try:
        tables = page.find_tables(table_settings=settings)
        return tables if tables else []
    except Exception as e:
        logger.debug(f"Stratégie '{strategy_name}' échouée: {e}")
        return []


def extract_pdf(pdf_path, table_columns=None, pages=None,
                strategy="auto", include_metadata=True):
    """
    Extrait le contenu complet d'un PDF : texte et tableaux dans l'ordre.

    Args:
        pdf_path: Chemin vers le fichier .pdf
        table_columns: Liste optionnelle d'indices de colonnes (0-based)
                       à extraire des tableaux.
                       Ex: [0, 2] = 1ère et 3ème colonne.
                       Si None, toutes les colonnes sont extraites.
        pages: Liste optionnelle de numéros de pages (1-based) à traiter.
               Si None, toutes les pages sont traitées.
        strategy: Stratégie de détection des tableaux:
                  - "standard" : lignes visibles (défaut)
                  - "text"     : alignement texte (tableaux sans bordures)
                  - "lines_strict" : lignes strictes uniquement
                  - "auto"     : essaye standard, puis text si aucun résultat
        include_metadata: Si True, inclut les métadonnées des tableaux

    Returns:
        Liste de blocs ordonnés :
        - {"type": "texte", "contenu": "...", "page": N}
        - {"type": "tableau", "numero": N, "page": N, "lignes": [...],
           "metadata": {...}}
    """
    content = []
    table_counter = 0
    pages_info = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info(f"PDF ouvert: {total_pages} pages — stratégie: {strategy}")

        for page_num, page in enumerate(pdf.pages, start=1):
            # Filtrer par pages si spécifié
            if pages and page_num not in pages:
                continue

            page_tables_count = 0
            page_texts_count = 0

            # --- Détecter les tableaux ---
            tables = []
            if strategy == "auto":
                # Essayer d'abord la stratégie standard
                tables = _try_extract_tables(page, "standard")
                if not tables:
                    # Fallback vers la détection par texte
                    tables = _try_extract_tables(page, "text")
                    if tables:
                        logger.info(
                            f"Page {page_num}: {len(tables)} tableau(x) "
                            f"détecté(s) avec stratégie 'text' (fallback)"
                        )
            else:
                tables = _try_extract_tables(page, strategy)

            table_bboxes = [t.bbox for t in tables]

            # --- Extraire les tableaux ---
            for table in tables:
                table_counter += 1
                block = _extract_table_data(
                    table, table_counter, page_num, table_columns
                )
                if block:
                    if not include_metadata:
                        block.pop("metadata", None)
                    content.append(block)
                    page_tables_count += 1

            # --- Extraire le texte hors tableaux ---
            if table_bboxes:
                filtered_page = page
                for bbox in table_bboxes:
                    filtered_page = filtered_page.filter(
                        lambda obj, bbox=bbox: not (
                            bbox[0] <= obj.get("x0", 0) <= bbox[2] and
                            bbox[1] <= obj.get("top", 0) <= bbox[3]
                        )
                    )
                text = filtered_page.extract_text()
            else:
                text = page.extract_text()

            if text and text.strip():
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                for para in paragraphs:
                    content.append({
                        "type": "texte",
                        "contenu": para,
                        "page": page_num
                    })
                    page_texts_count += 1

            pages_info.append({
                "page": page_num,
                "nb_textes": page_texts_count,
                "nb_tableaux": page_tables_count,
            })

    nb_textes = sum(1 for b in content if b['type'] == 'texte')
    nb_tableaux = sum(1 for b in content if b['type'] == 'tableau')
    logger.info(
        f"Extraction PDF terminée: {len(content)} blocs "
        f"({nb_textes} textes, {nb_tableaux} tableaux)"
    )

    return content, {
        "total_pages": total_pages if 'total_pages' in dir() else len(pages_info),
        "pages_traitees": len(pages_info),
        "total_blocs": len(content),
        "nb_textes": nb_textes,
        "nb_tableaux": nb_tableaux,
        "strategie_utilisee": strategy,
        "detail_pages": pages_info,
    }
