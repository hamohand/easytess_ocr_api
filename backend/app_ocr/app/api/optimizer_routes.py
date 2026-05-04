import os
from flask import Blueprint, request, jsonify, current_app, Response
import json
import logging
import time
from app.services.zone_optimizer import (
    optimiser_zone,
    preparer_image_de_travail
)

logger = logging.getLogger(__name__)

optimizer_bp = Blueprint('optimizer', __name__, url_prefix='/api/optimizer')

@optimizer_bp.route('/run', methods=['POST'])
def run_optimizer():
    """
    Run zone optimization.
    Expects JSON body:
    {
       "entity_name": "cni_algo_recto_001",
       "zone_name": "nom",
       "texte_attendu": "حمرون",
       "use_tesseract": true,
       "use_easyocr": false
    }
    """
    data = request.json
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    entity_name = data.get('entity_name')
    zone_name = data.get('zone_name')
    texte_attendu = data.get('texte_attendu')
    use_tesseract = data.get('use_tesseract', True)
    use_easyocr = data.get('use_easyocr', False)

    if not entity_name or not zone_name or not texte_attendu:
        return jsonify({"error": "entity_name, zone_name and texte_attendu are required"}), 400

    # Retrieve entity info
    entity = current_app.entity_manager.charger_entite(entity_name)
    if not entity:
        return jsonify({"error": f"Entity {entity_name} not found"}), 404

    # Get image file (reference)
    image_file = entity.get('image_reference')
    if not image_file or not os.path.exists(image_file):
        # Fallback to local entities folder just in case
        image_file = os.path.join(current_app.config['ENTITIES_FOLDER'], entity_name, 'reference.jpeg')
        if not os.path.exists(image_file):
            image_file = os.path.join(current_app.config['ENTITIES_FOLDER'], entity_name, 'reference.png')
            
    if not image_file or not os.path.exists(image_file):
        return jsonify({"error": f"Reference image for {entity_name} not found"}), 404

    # Extract target zone
    target_zone = next((z for z in entity.get('zones', []) if z['nom'] == zone_name), None)
    if not target_zone:
        return jsonify({"error": f"Zone {zone_name} not found in entity {entity_name}"}), 404
    if not target_zone:
        return jsonify({"error": f"Zone {zone_name} not found in entity {entity_name}"}), 404

    coords_base = target_zone.get('coords')
    lang = target_zone.get('lang', 'ara')
    preprocess = target_zone.get('preprocess', 'arabic_textured')
    expected_format = target_zone.get('expected_format', 'auto')
    char_filter = target_zone.get('char_filter', 'none')
    margin = target_zone.get('margin', 0)

    stop_threshold = data.get('stop_threshold')
    if stop_threshold is not None:
        try:
            stop_threshold = float(stop_threshold)
        except ValueError:
            stop_threshold = None

    try:
        # Prepare image
        image_de_travail, cadre_info, crop_a_nettoyer = preparer_image_de_travail(image_file, entity)
        
        # Optimize zone
        debut_zone = time.time()
        resultat = optimiser_zone(
            image_path=image_de_travail,
            nom_zone=zone_name,
            coords_base=coords_base,
            texte_attendu=texte_attendu,
            lang=lang,
            preprocess=preprocess,
            expected_format=expected_format,
            char_filter=char_filter,
            margin=margin,
            use_tesseract=use_tesseract,
            use_easyocr=use_easyocr,
            stop_threshold=stop_threshold
        )
        duree_zone = time.time() - debut_zone
        resultat['duree_secondes'] = round(duree_zone, 1)

        # Cleanup crop
        if crop_a_nettoyer and os.path.exists(crop_a_nettoyer):
            try:
                os.remove(crop_a_nettoyer)
            except Exception:
                pass

        return jsonify(resultat)

    except Exception as e:
        logger.error(f"Error during optimization: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
