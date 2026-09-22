"""
Endpoint dédié mobile : extraction des noms arabes par recherche de mots-clés.
Utilise PaddleOCR pour scanner toute l'image et trouver les étiquettes اللقب et الاسم
puis prend la valeur à côté. Aucune coordonnée fixe.
"""
from flask import Blueprint, request, jsonify, current_app
import os
import logging
import re

logger = logging.getLogger(__name__)

mobile_ocr_bp = Blueprint('mobile_ocr', __name__)


def _resolve_image_path(filename):
    """Cherche un fichier dans uploads_temp d'abord, puis dans uploads."""
    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    perm_folder = current_app.config['UPLOAD_FOLDER']
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
    temp_path = os.path.join(temp_folder, filename)
    if os.path.exists(temp_path):
        return temp_path
    perm_path = os.path.join(perm_folder, filename)
    if os.path.exists(perm_path):
        return perm_path
    return None


# Étiquettes à chercher (avec variantes pour tolérer les erreurs OCR)
# PaddleOCR lit souvent l'arabe en miroir (LTR au lieu de RTL), donc on ajoute les versions inversées
LABELS_NOM = ['اللقب', 'للقب', 'القب', 'بقللا', 'بقلا', 'بقتلا']
LABELS_PRENOM = ['الاسم', 'الإسم', 'لاسم', 'مسالا', 'مسإلا', 'مسلا']


def _reverse_arabic(text):
    """Inverse le texte arabe caractère par caractère (corrige le bug LTR de PaddleOCR)."""
    return text[::-1]


def _fix_arabic_text(text):
    """Si le texte arabe semble inversé, le remettre à l'endroit."""
    # Chercher les marqueurs connus de la CNI dans les deux sens
    markers_normal = ['اللقب', 'الاسم', 'الوطني', 'الجمهورية', 'تاريخ']
    markers_reversed = ['بقللا', 'مسالا', 'ينطولا', 'ةيروهمجلا', 'خيرات']
    
    normal_hits = sum(1 for m in markers_normal if m in text)
    reversed_hits = sum(1 for m in markers_reversed if m in text)
    
    if reversed_hits > normal_hits:
        return _reverse_arabic(text)
    return text


def trouver_etiquette(mots, labels):
    """Trouve le mot qui correspond le mieux à une des étiquettes."""
    from rapidfuzz import fuzz
    meilleur = None
    meilleur_score = 0
    for mot in mots:
        for label in labels:
            # partial_ratio gère le cas où l'étiquette est contenue dans un bloc plus long
            score = fuzz.partial_ratio(label, mot['text'])
            if score > meilleur_score and score >= 70:
                meilleur_score = score
                meilleur = mot
    return meilleur, meilleur_score


def extraire_valeur(mots, etiquette, direction='gauche'):
    """
    Prend tous les mots sur la même ligne que l'étiquette,
    du côté indiqué (gauche = à gauche de l'étiquette, pour l'arabe RTL).
    Si l'étiquette contient aussi la valeur (ex: "اللقب : حمرون"), l'extraire directement.
    """
    from rapidfuzz import fuzz
    if not etiquette:
        return ''

    # Cas 1 : L'étiquette contient le label ET la valeur (PaddleOCR lit tout en un bloc)
    text = etiquette['text']
    for sep in [':', '：', ' :']:
        if sep in text:
            parts = text.split(sep, 1)
            if len(parts) == 2:
                valeur = parts[0].strip()  # En arabe RTL, la valeur est AVANT les deux-points
                label_part = parts[1].strip()
                # Vérifier quel côté est le label
                is_label_right = any(fuzz.partial_ratio(l, label_part) >= 70 for l in LABELS_NOM + LABELS_PRENOM)
                is_label_left = any(fuzz.partial_ratio(l, valeur) >= 70 for l in LABELS_NOM + LABELS_PRENOM)
                if is_label_right and valeur and not is_label_left:
                    return valeur
                if is_label_left and label_part and not is_label_right:
                    return label_part

    # Cas 2 : Chercher les mots adjacents sur la même ligne
    tolerance_y = etiquette['h'] * 1.2
    mots_ligne = []

    for mot in mots:
        if mot is etiquette:
            continue
        if abs(mot['cy'] - etiquette['cy']) < tolerance_y:
            if direction == 'gauche' and mot['cx'] < etiquette['cx']:
                mots_ligne.append(mot)
            elif direction == 'droite' and mot['cx'] > etiquette['cx']:
                mots_ligne.append(mot)

    # Trier de droite à gauche (RTL arabe)
    mots_ligne.sort(key=lambda m: m['cx'], reverse=True)

    textes = []
    for m in mots_ligne:
        t = m['text'].strip()
        is_label = any(fuzz.partial_ratio(t, l) >= 70 for l in LABELS_NOM + LABELS_PRENOM)
        if not is_label and len(t) > 1:
            textes.append(t)

    return ' '.join(textes)


@mobile_ocr_bp.route('/api/ocr-noms-arabes', methods=['POST'])
def api_ocr_noms_arabes():
    """
    Extrait nom et prénom arabes d'une CNI en cherchant les mots-clés اللقب et الاسم.
    Attend un JSON avec 'filename' (fichier déjà uploadé via /api/upload).
    """
    from app.services.ocr_engine_v2 import get_paddleocr_reader, PADDLEOCR_DISPONIBLE

    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({"success": False, "error": "Champ 'filename' manquant"}), 400

    filename = data['filename']
    image_path = _resolve_image_path(filename)
    if not image_path:
        return jsonify({"success": False, "error": f"Fichier '{filename}' introuvable"}), 404

    if not PADDLEOCR_DISPONIBLE:
        return jsonify({"success": False, "error": "PaddleOCR non disponible"}), 500

    try:
        reader = get_paddleocr_reader('ara+fra')
        if not reader:
            return jsonify({"success": False, "error": "Lecteur PaddleOCR indisponible"}), 500

        ocr_results = reader.ocr(image_path, cls=True)

        if not ocr_results or not ocr_results[0]:
            return jsonify({"success": False, "error": "Aucun texte détecté"}), 400

        # Construire la liste des mots avec positions
        mots = []
        for line in ocr_results[0]:
            box = line[0]
            text = line[1][0]
            conf = line[1][1]
            cy = (box[0][1] + box[2][1]) / 2
            cx = (box[0][0] + box[2][0]) / 2
            h = abs(box[2][1] - box[0][1])
            mots.append({'text': text, 'cx': cx, 'cy': cy, 'h': h, 'conf': conf})

        # Détecter si le texte arabe est inversé (bug PaddleOCR LTR)
        all_text_joined = ' '.join(m['text'] for m in mots)
        is_reversed = False
        markers_normal = ['اللقب', 'الاسم', 'الوطني']
        markers_reversed = ['بقللا', 'مسالا', 'ينطولا', 'بقتلا', 'مسإلا']
        normal_hits = sum(1 for m in markers_normal if m in all_text_joined)
        reversed_hits = sum(1 for m in markers_reversed if m in all_text_joined)
        if reversed_hits > normal_hits:
            is_reversed = True
            logger.info("🔄 Texte arabe INVERSÉ détecté — correction en cours")
            for m in mots:
                m['text_original'] = m['text']
                m['text'] = m['text'][::-1]

        logger.info(f"📄 PaddleOCR mobile scan: {len(mots)} mots détectés (inversé={is_reversed})")
        all_texts = []
        for m in mots:
            logger.info(f"   '{m['text']}' cx={m['cx']:.0f} cy={m['cy']:.0f}")
            all_texts.append(m['text'])

        # Trouver les étiquettes et extraire les valeurs
        etiq_nom, score_nom = trouver_etiquette(mots, LABELS_NOM)
        etiq_prenom, score_prenom = trouver_etiquette(mots, LABELS_PRENOM)

        nom = extraire_valeur(mots, etiq_nom, 'gauche')
        prenom = extraire_valeur(mots, etiq_prenom, 'gauche')

        # Nettoyage
        nom = re.sub(r'[:\-/\\|]', '', nom).strip()
        prenom = re.sub(r'[:\-/\\|]', '', prenom).strip()

        logger.info(f"🎯 Résultat mobile: nom='{nom}', prenom='{prenom}'")

        return jsonify({
            "success": True,
            "nom": nom,
            "prenom": prenom,
            "debug": {
                "etiq_nom_found": etiq_nom['text'] if etiq_nom else None,
                "etiq_nom_score": score_nom,
                "etiq_prenom_found": etiq_prenom['text'] if etiq_prenom else None,
                "etiq_prenom_score": score_prenom,
                "total_mots": len(mots),
                "all_texts": all_texts
            }
        })

    except Exception as e:
        logger.error(f"Erreur OCR noms arabes: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

