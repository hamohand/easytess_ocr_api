"""
Service d'extraction de contenu Word (.docx)
Extrait le texte et les tableaux dans l'ordre d'apparition.
Supporte:
  - Les vrais tableaux Word (w:tbl)
  - Les pseudo-tableaux (paragraphes avec tabulations)
"""
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import logging

logger = logging.getLogger(__name__)

# Nombre minimum de tabulations dans un paragraphe pour le considérer
# comme une ligne de pseudo-tableau
MIN_TABS_FOR_TABLE = 1


def _iter_block_items(parent):
    """
    Parcourt les éléments du document dans l'ordre d'apparition
    (paragraphes ET tableaux mélangés).
    """
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


def _is_tab_row(text):
    """Vérifie si un paragraphe ressemble à une ligne de tableau tabulé."""
    return text.count('\t') >= MIN_TABS_FOR_TABLE


def _build_tab_table_block(tab_lines, table_counter, table_columns):
    """
    Construit un bloc 'tableau' à partir de lignes tabulées.
    Chaque ligne est découpée sur les tabulations.
    """
    lignes = []
    for line in tab_lines:
        parts = [p.strip() for p in line.split('\t')]
        # Déterminer les colonnes à extraire
        cols = table_columns if table_columns else list(range(len(parts)))
        row_data = {}
        for col_idx in cols:
            if 0 <= col_idx < len(parts):
                key = f"col_{col_idx:02d}"
                row_data[key] = parts[col_idx]
        if row_data:
            lignes.append(row_data)

    if not lignes:
        return None

    return {
        "type": "tableau",
        "numero": table_counter,
        "lignes": lignes
    }


def extract_document(docx_path, table_columns=None):
    """
    Extrait le contenu complet d'un document Word.

    Args:
        docx_path: Chemin vers le fichier .docx
        table_columns: Liste optionnelle d'indices de colonnes (0-based)
                       à extraire des tableaux.
                       Ex: [0, 2] = 1ère et 3ème colonne.
                       Si None, toutes les colonnes sont extraites.

    Returns:
        Liste de blocs ordonnés :
        - {"type": "texte", "contenu": "..."}
        - {"type": "tableau", "numero": N, "lignes": [...]}
    """
    doc = Document(docx_path)
    content = []
    table_counter = 0

    # Buffer pour accumuler les lignes tabulées consécutives
    tab_buffer = []

    def flush_tab_buffer():
        """Vide le buffer de lignes tabulées en créant un bloc tableau."""
        nonlocal table_counter
        if tab_buffer:
            table_counter += 1
            block = _build_tab_table_block(tab_buffer, table_counter, table_columns)
            if block:
                content.append(block)
            tab_buffer.clear()

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                continue

            if _is_tab_row(text):
                # Accumuler les lignes tabulées
                tab_buffer.append(text)
            else:
                # Texte normal : d'abord vider le buffer tabulé
                flush_tab_buffer()
                content.append({
                    "type": "texte",
                    "contenu": text
                })

        elif isinstance(block, Table):
            # Vider le buffer tabulé avant un vrai tableau
            flush_tab_buffer()

            table_counter += 1
            rows = block.rows
            if not rows:
                continue

            nb_cols = len(rows[0].cells)
            cols = table_columns if table_columns else list(range(nb_cols))
            cols = [c for c in cols if 0 <= c < nb_cols]

            if not cols:
                logger.warning(
                    f"Tableau {table_counter}: aucune colonne valide parmi {table_columns} "
                    f"(le tableau a {nb_cols} colonnes)"
                )
                continue

            lignes = []
            for row in rows:
                cells = row.cells
                row_data = {}
                for col_idx in cols:
                    if col_idx < len(cells):
                        key = f"col_{col_idx:02d}"
                        row_data[key] = cells[col_idx].text.strip()
                lignes.append(row_data)

            content.append({
                "type": "tableau",
                "numero": table_counter,
                "lignes": lignes
            })

    # Ne pas oublier le dernier buffer
    flush_tab_buffer()

    nb_textes = sum(1 for b in content if b['type'] == 'texte')
    nb_tableaux = sum(1 for b in content if b['type'] == 'tableau')
    logger.info(
        f"Extraction terminée: {len(content)} blocs "
        f"({nb_textes} textes, {nb_tableaux} tableaux)"
    )
    return content
