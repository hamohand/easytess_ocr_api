"""
Service d'extraction de contenu Word (.docx)
Extrait le texte et les tableaux dans l'ordre d'apparition.
"""
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
import logging

logger = logging.getLogger(__name__)


def _iter_block_items(parent):
    """
    Parcourt les éléments du document dans l'ordre d'apparition
    (paragraphes ET tableaux mélangés), contrairement à
    doc.paragraphs / doc.tables qui les séparent.
    """
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)


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
        - {"type": "tableau", "numero": N, "en_tetes": [...], "lignes": [...]}
    """
    doc = Document(docx_path)
    content = []
    table_counter = 0

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                content.append({
                    "type": "texte",
                    "contenu": text
                })

        elif isinstance(block, Table):
            table_counter += 1
            rows = block.rows
            if not rows:
                continue

            # Déterminer les colonnes à extraire
            nb_cols = len(rows[0].cells)
            cols = table_columns if table_columns else list(range(nb_cols))

            # Filtrer les indices invalides
            cols = [c for c in cols if 0 <= c < nb_cols]

            if not cols:
                logger.warning(
                    f"Tableau {table_counter}: aucune colonne valide parmi {table_columns} "
                    f"(le tableau a {nb_cols} colonnes)"
                )
                continue

            # En-têtes depuis la première ligne
            headers = [rows[0].cells[col_idx].text.strip() for col_idx in cols]

            # Données (lignes suivantes)
            lignes = []
            for row in rows[1:]:
                cells = row.cells
                row_data = {}
                for h_idx, col_idx in enumerate(cols):
                    if col_idx < len(cells):
                        row_data[headers[h_idx]] = cells[col_idx].text.strip()
                lignes.append(row_data)

            content.append({
                "type": "tableau",
                "numero": table_counter,
                "en_tetes": headers,
                "lignes": lignes
            })

    logger.info(
        f"Extraction terminée: {len(content)} blocs "
        f"({sum(1 for b in content if b['type'] == 'texte')} textes, "
        f"{table_counter} tableaux)"
    )
    return content
