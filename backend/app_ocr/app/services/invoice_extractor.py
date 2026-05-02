"""
Service d'extraction de factures par OCR.

Extrait la liste des articles (colonne "Désignation" / "Intitulé") d'une image
de facture en utilisant Tesseract OCR avec analyse positionnelle.

Algorithme:
  1. OCR global avec positions (pytesseract.image_to_data)
  2. Regroupement des mots en lignes par proximité Y
  3. Détection de l'en-tête du tableau par mots-clés
  4. Identification des bornes de la colonne "Désignation"
  5. Extraction des articles ligne par ligne
  6. Arrêt aux mots-clés de fin de tableau (total, sous-total, etc.)
"""

import os
import re
import logging
import uuid
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# Configuration des mots-clés
# ═══════════════════════════════════════════════════════════

# Mots-clés pour identifier la colonne "Désignation" dans l'en-tête
DESIGNATION_KEYWORDS = [
    'désignation', 'designation', 'intitulé', 'intitule',
    'description', 'article', 'libellé', 'libelle',
    'produit', 'service', 'détail', 'detail',
    'articles', 'désignations', 'libellés',
    'prestation', 'prestations',
]

# Mots-clés qui indiquent d'autres colonnes de la facture (pas la désignation)
OTHER_COLUMN_KEYWORDS = [
    'quantité', 'quantite', 'qté', 'qte', 'qty',
    'prix', 'p.u.', 'pu', 'unitaire',
    'montant', 'total', 'ht', 'ttc',
    'tva', 'taxe', 'taux',
    'remise', 'réduction', 'reduction',
    'référence', 'reference', 'réf', 'ref', 'n°', 'code',
    'unité', 'unite', 'u.m.',
    'nbre', 'nombre',
]

# Mots-clés qui signalent la fin du tableau d'articles
FOOTER_KEYWORDS = [
    'total', 'sous-total', 'sous total', 'subtotal',
    'montant ht', 'montant ttc', 'total ht', 'total ttc',
    'net à payer', 'net a payer',
    'total général', 'total general',
    'arrêté', 'arrete',
    'المجموع', 'المبلغ الإجمالي',
]


# ═══════════════════════════════════════════════════════════
# Fonctions utilitaires
# ═══════════════════════════════════════════════════════════

def _normalize_text(text):
    """Normalise un texte pour la comparaison (minuscule, sans accents superflus)."""
    return text.strip().lower()


def _is_designation_keyword(text):
    """Vérifie si un texte correspond à un mot-clé de désignation."""
    norm = _normalize_text(text)
    return any(kw in norm for kw in DESIGNATION_KEYWORDS)


def _is_footer_keyword(text):
    """Vérifie si un texte correspond à un mot-clé de fin de tableau."""
    norm = _normalize_text(text)
    return any(kw in norm for kw in FOOTER_KEYWORDS)


def _is_numeric_or_monetary(text):
    """Vérifie si un texte est principalement numérique ou monétaire."""
    cleaned = text.strip().replace(' ', '').replace(',', '.').replace('€', '').replace('$', '').replace('DA', '').replace('دج', '')
    # Pattern: nombre optionnel avec décimales, pourcentage
    return bool(re.match(r'^[\d\s.,€$%\-]+$', cleaned)) and len(cleaned) > 0


# ═══════════════════════════════════════════════════════════
# OCR global avec positions
# ═══════════════════════════════════════════════════════════

def _ocr_with_positions(image_path, lang='fra'):
    """
    Effectue un OCR global et retourne tous les mots avec leurs positions.
    
    Returns:
        list[dict]: Mots avec {text, x, y, width, height, conf, line_num, block_num}
        tuple: (img_width, img_height)
    """
    import pytesseract

    img = Image.open(image_path)
    img_w, img_h = img.size

    try:
        data = pytesseract.image_to_data(
            img, lang=lang, output_type=pytesseract.Output.DICT
        )

        mots = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i]) if data['conf'][i] != '-1' else 0

            if text and conf > 10:  # Seuil bas pour ne pas perdre de texte
                mots.append({
                    'text': text,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'conf': conf,
                    'block_num': data['block_num'][i],
                    'line_num': data['line_num'][i],
                    'word_num': data['word_num'][i],
                })

        logger.info(f"📄 OCR facture: {len(mots)} mots détectés ({img_w}x{img_h}px)")
        return mots, (img_w, img_h)

    except Exception as e:
        logger.error(f"Erreur OCR facture: {e}")
        return [], (img_w, img_h)


# ═══════════════════════════════════════════════════════════
# Regroupement en lignes
# ═══════════════════════════════════════════════════════════

def _group_words_into_lines(mots, tolerance_factor=0.5):
    """
    Regroupe les mots en lignes par proximité Y.
    
    Args:
        mots: Liste de mots avec positions
        tolerance_factor: Facteur de tolérance (fraction de la hauteur médiane)
    
    Returns:
        list[list[dict]]: Lignes de mots, triées par Y puis X
    """
    if not mots:
        return []

    # Calculer la hauteur médiane des mots pour la tolérance
    heights = [m['height'] for m in mots if m['height'] > 0]
    if not heights:
        return []
    median_h = np.median(heights)
    tolerance = median_h * tolerance_factor

    # Trier par Y (haut) puis X (gauche)
    sorted_mots = sorted(mots, key=lambda m: (m['y'], m['x']))

    lines = []
    current_line = [sorted_mots[0]]
    current_y = sorted_mots[0]['y']

    for mot in sorted_mots[1:]:
        # Même ligne si la différence Y est dans la tolérance
        if abs(mot['y'] - current_y) <= tolerance:
            current_line.append(mot)
        else:
            # Trier la ligne courante par X
            current_line.sort(key=lambda m: m['x'])
            lines.append(current_line)
            current_line = [mot]
            current_y = mot['y']

    # Dernière ligne
    if current_line:
        current_line.sort(key=lambda m: m['x'])
        lines.append(current_line)

    return lines


def _line_text(line):
    """Reconstitue le texte complet d'une ligne."""
    return ' '.join(m['text'] for m in line)


def _line_y_center(line):
    """Retourne le Y central d'une ligne."""
    ys = [m['y'] + m['height'] / 2 for m in line]
    return np.mean(ys)


# ═══════════════════════════════════════════════════════════
# Détection de l'en-tête et des colonnes
# ═══════════════════════════════════════════════════════════

def _find_header_line(lines):
    """
    Trouve la ligne d'en-tête du tableau contenant le mot-clé "Désignation".
    
    Returns:
        tuple: (index_ligne, mot_designation) ou (None, None)
    """
    for idx, line in enumerate(lines):
        full_text = _line_text(line)
        
        # Chercher le mot-clé de désignation dans la ligne
        for mot in line:
            if _is_designation_keyword(mot['text']):
                logger.info(f"🎯 En-tête trouvé ligne {idx}: '{full_text}'")
                return idx, mot
        
        # Chercher aussi dans le texte reconstitué (mots-clés multi-mots)
        norm_text = _normalize_text(full_text)
        for kw in DESIGNATION_KEYWORDS:
            if kw in norm_text:
                # Trouver le mot le plus proche du début du keyword
                kw_pos = norm_text.find(kw)
                # Estimer la position X du mot-clé
                best_mot = None
                char_count = 0
                for mot in line:
                    mot_text_len = len(mot['text'])
                    if char_count <= kw_pos < char_count + mot_text_len + 1:
                        best_mot = mot
                        break
                    char_count += mot_text_len + 1  # +1 pour l'espace
                
                if best_mot is None:
                    best_mot = line[0]
                
                logger.info(f"🎯 En-tête trouvé ligne {idx} (multi-mots): '{full_text}'")
                return idx, best_mot
    
    return None, None


def _detect_designation_bounds(header_line, designation_mot, img_width):
    """
    Détermine les bornes X de la colonne "Désignation" à partir de la ligne d'en-tête.
    
    Stratégie:
    - Identifier les mots d'en-tête correspondant à d'autres colonnes
    - La colonne "Désignation" s'étend entre les colonnes adjacentes
    
    Returns:
        tuple: (x_min, x_max) en pixels
    """
    # Trouver les bornes des autres colonnes
    other_column_positions = []
    
    for mot in header_line:
        if mot is designation_mot:
            continue
        mot_norm = _normalize_text(mot['text'])
        for kw in OTHER_COLUMN_KEYWORDS:
            if kw in mot_norm or mot_norm in kw:
                other_column_positions.append({
                    'x': mot['x'],
                    'x_right': mot['x'] + mot['width'],
                    'text': mot['text']
                })
                break
    
    # Position du mot "Désignation"
    desig_x = designation_mot['x']
    desig_x_right = designation_mot['x'] + designation_mot['width']
    
    # Trouver la borne gauche = max(bord droit des colonnes à gauche de la désignation)
    cols_a_gauche = [c for c in other_column_positions if c['x_right'] <= desig_x]
    if cols_a_gauche:
        x_min = max(c['x_right'] for c in cols_a_gauche)
    else:
        # Pas de colonne à gauche → commencer au début de la ligne
        x_min = max(0, min(m['x'] for m in header_line) - 10)
    
    # Trouver la borne droite = min(bord gauche des colonnes à droite de la désignation)
    cols_a_droite = [c for c in other_column_positions if c['x'] >= desig_x_right]
    if cols_a_droite:
        x_max = min(c['x'] for c in cols_a_droite)
    else:
        # Pas de colonne à droite → aller jusqu'au bout
        x_max = img_width
    
    # Ajouter une marge de sécurité
    margin = 5
    x_min = max(0, x_min - margin)
    x_max = min(img_width, x_max + margin)
    
    logger.info(
        f"📏 Colonne Désignation: x=[{x_min:.0f}, {x_max:.0f}]px "
        f"(largeur={x_max - x_min:.0f}px sur {img_width}px)"
    )
    
    return x_min, x_max


# ═══════════════════════════════════════════════════════════
# Extraction des articles
# ═══════════════════════════════════════════════════════════

def _extract_articles(lines, header_idx, x_min, x_max):
    """
    Extrait les articles des lignes sous l'en-tête.
    
    Pour chaque ligne, ne retient que les mots dont le centre X est 
    dans la zone de la colonne "Désignation".
    
    Args:
        lines: Toutes les lignes OCR
        header_idx: Index de la ligne d'en-tête
        x_min, x_max: Bornes X de la colonne désignation
    
    Returns:
        list[dict]: Articles extraits [{designation, confiance, ligne_y, ...}]
    """
    articles = []
    
    for idx in range(header_idx + 1, len(lines)):
        line = lines[idx]
        full_text = _line_text(line)
        
        # Vérifier si c'est une ligne de pied de tableau
        if _is_footer_keyword(full_text):
            logger.info(f"🛑 Fin du tableau détectée ligne {idx}: '{full_text}'")
            break
        
        # Filtrer les mots dans la zone de la colonne Désignation
        mots_designation = []
        for mot in line:
            mot_center_x = mot['x'] + mot['width'] / 2
            # Le mot est dans la colonne si son centre est dans les bornes
            if x_min <= mot_center_x <= x_max:
                # Exclure les valeurs purement numériques/monétaires
                if not _is_numeric_or_monetary(mot['text']):
                    mots_designation.append(mot)
        
        if mots_designation:
            designation_text = ' '.join(m['text'] for m in mots_designation)
            avg_conf = np.mean([m['conf'] for m in mots_designation])
            line_y = _line_y_center(line)
            
            # Ne pas ajouter les lignes vides ou trop courtes (bruit)
            if len(designation_text.strip()) > 1:
                articles.append({
                    'designation': designation_text.strip(),
                    'confiance': round(float(avg_conf), 1),
                    'position_y': round(float(line_y), 1),
                    'nb_mots': len(mots_designation),
                })
    
    return articles


# ═══════════════════════════════════════════════════════════
# Fonction principale d'extraction
# ═══════════════════════════════════════════════════════════

def extraire_facture(image_path, lang='fra'):
    """
    Extrait la liste des articles (désignations) d'une image de facture.
    
    Args:
        image_path: Chemin vers l'image (ou PDF converti en image)
        lang: Langue OCR (fra, ara+fra, eng)
    
    Returns:
        dict: {
            'success': bool,
            'articles': [{'designation': str, 'confiance': float, ...}],
            'nb_articles': int,
            'en_tete_detecte': str | None,
            'colonne_designation': {'x_min': float, 'x_max': float} | None,
            'total_mots_ocr': int,
            'total_lignes': int,
            'image_dimensions': {'width': int, 'height': int},
            'debug': {...}  # Infos de debug
        }
    """
    logger.info(f"🧾 Extraction facture: {image_path} (lang={lang})")
    
    # 1. OCR global
    mots, img_dims = _ocr_with_positions(image_path, lang=lang)
    img_w, img_h = img_dims
    
    if not mots:
        return {
            'success': False,
            'error': "Aucun texte détecté dans l'image. Vérifiez la qualité de l'image.",
            'articles': [],
            'nb_articles': 0,
            'en_tete_detecte': None,
            'colonne_designation': None,
            'total_mots_ocr': 0,
            'total_lignes': 0,
            'image_dimensions': {'width': img_w, 'height': img_h},
        }
    
    # 2. Regrouper en lignes
    lines = _group_words_into_lines(mots)
    logger.info(f"📊 {len(lines)} lignes regroupées à partir de {len(mots)} mots")
    
    # 3. Trouver l'en-tête
    header_idx, designation_mot = _find_header_line(lines)
    
    if header_idx is None:
        # Pas d'en-tête trouvé — retourner toutes les lignes OCR brutes pour debug
        all_lines_text = [_line_text(line) for line in lines]
        return {
            'success': False,
            'error': (
                "En-tête de tableau non trouvé. "
                "Aucun mot-clé de désignation détecté "
                f"(cherché: {', '.join(DESIGNATION_KEYWORDS[:5])}...)."
            ),
            'articles': [],
            'nb_articles': 0,
            'en_tete_detecte': None,
            'colonne_designation': None,
            'total_mots_ocr': len(mots),
            'total_lignes': len(lines),
            'image_dimensions': {'width': img_w, 'height': img_h},
            'debug': {
                'lignes_ocr': all_lines_text[:30],  # Max 30 lignes pour le debug
            }
        }
    
    # 4. Détecter les bornes de la colonne
    header_line = lines[header_idx]
    x_min, x_max = _detect_designation_bounds(header_line, designation_mot, img_w)
    
    # 5. Extraire les articles
    articles = _extract_articles(lines, header_idx, x_min, x_max)
    
    logger.info(f"✅ {len(articles)} articles extraits de la facture")
    
    return {
        'success': True,
        'articles': articles,
        'nb_articles': len(articles),
        'en_tete_detecte': _line_text(header_line),
        'colonne_designation': {
            'x_min': round(x_min / img_w, 4),
            'x_max': round(x_max / img_w, 4),
        },
        'total_mots_ocr': len(mots),
        'total_lignes': len(lines),
        'image_dimensions': {'width': img_w, 'height': img_h},
    }


def extraire_facture_depuis_pdf(pdf_path, lang='fra', dpi=300):
    """
    Extrait les articles d'une facture PDF.
    Convertit chaque page en image puis applique l'extraction OCR.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        lang: Langue OCR
        dpi: Résolution pour la conversion PDF → image
    
    Returns:
        dict: Même structure que extraire_facture() avec champ 'pages' supplémentaire
    """
    import pypdfium2 as pdfium
    
    logger.info(f"🧾 Extraction facture PDF: {pdf_path} (lang={lang}, dpi={dpi})")
    
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        nb_pages = len(pdf)
        
        if nb_pages < 1:
            return {
                'success': False,
                'error': 'Le PDF est vide',
                'articles': [],
                'nb_articles': 0,
            }
        
        all_articles = []
        pages_results = []
        en_tete_global = None
        colonne_global = None
        
        temp_dir = os.path.dirname(pdf_path)
        temp_images = []
        
        for page_num in range(nb_pages):
            # Convertir la page en image
            page = pdf[page_num]
            scale = dpi / 72
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            
            # Sauvegarder temporairement
            temp_filename = f"invoice_page_{uuid.uuid4().hex[:8]}.jpg"
            temp_path = os.path.join(temp_dir, temp_filename)
            pil_image.save(temp_path, format="JPEG", quality=95)
            temp_images.append(temp_path)
            
            # Extraire
            result = extraire_facture(temp_path, lang=lang)
            
            page_result = {
                'page': page_num + 1,
                'nb_articles': result.get('nb_articles', 0),
                'en_tete_detecte': result.get('en_tete_detecte'),
                'articles': result.get('articles', []),
            }
            pages_results.append(page_result)
            
            # Accumuler les articles
            for article in result.get('articles', []):
                article_with_page = {**article, 'page': page_num + 1}
                all_articles.append(article_with_page)
            
            # Garder le premier en-tête trouvé
            if en_tete_global is None and result.get('en_tete_detecte'):
                en_tete_global = result['en_tete_detecte']
                colonne_global = result.get('colonne_designation')
        
        # Nettoyage des images temporaires
        for temp_path in temp_images:
            try:
                os.remove(temp_path)
            except Exception:
                pass
        
        logger.info(f"✅ PDF {nb_pages} pages: {len(all_articles)} articles extraits au total")
        
        return {
            'success': len(all_articles) > 0,
            'articles': all_articles,
            'nb_articles': len(all_articles),
            'nb_pages': nb_pages,
            'en_tete_detecte': en_tete_global,
            'colonne_designation': colonne_global,
            'pages': pages_results,
            'error': None if all_articles else "Aucun article trouvé dans le PDF",
        }
    
    except Exception as e:
        logger.error(f"Erreur extraction facture PDF: {e}")
        return {
            'success': False,
            'error': f"Erreur lors du traitement du PDF: {str(e)}",
            'articles': [],
            'nb_articles': 0,
        }
