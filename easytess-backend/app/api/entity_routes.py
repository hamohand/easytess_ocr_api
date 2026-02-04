from flask import Blueprint, request, jsonify, session, current_app, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
from app.utils.pdf_utils import convert_pdf_to_image
from app.services.ocr_engine import ocr_global_avec_positions, detecter_ancres

entity_bp = Blueprint('entity', __name__)

def get_manager():
    return current_app.entity_manager

@entity_bp.route('/api/entites', methods=['GET'])
def lister_entites():
    entites = get_manager().lister_entites()
    return jsonify(entites)

@entity_bp.route('/api/entite/<nom>', methods=['GET'])
def get_entite(nom):
    entite = get_manager().charger_entite(nom)
    if entite:
        return jsonify(entite)
    return jsonify({'error': 'Not found'}), 404

@entity_bp.route('/api/set-entite-active/<nom>', methods=['POST'])
def set_entite_active(nom):
    if nom == 'none':
        session.pop('entite_active', None)
        return jsonify({'success': True, 'active': None})
    
    entite = get_manager().charger_entite(nom)
    if entite:
        session['entite_active'] = entite
        return jsonify({'success': True, 'active': entite['nom']})
    return jsonify({'error': 'Not found'}), 404

@entity_bp.route('/api/upload-image-entite', methods=['POST'])
def upload_image_entite():
    if 'image' not in request.files:
        return jsonify({'error': 'No file'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No filename'}), 400
        
    filename = secure_filename(file.filename)
    saved_filename = f"temp_entite_{str(uuid.uuid4())}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)
    
    # Conversion PDF -> Image si nécessaire
    if filename.lower().endswith('.pdf'):
        try:
            image_filename = f"{os.path.splitext(saved_filename)[0]}.jpg"
            image_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
            convert_pdf_to_image(filepath, image_filepath)
            
            # On bascule sur l'image pour la suite
            saved_filename = image_filename
            filepath = image_filepath
        except Exception as e:
            return jsonify({'error': f'Erreur lors de la conversion PDF: {str(e)}'}), 500
    
    try:
        with Image.open(filepath) as img:
            width, height = img.size
    except:
        width, height = 0, 0
    
    session['temp_image_path'] = filepath
    
    # Construct URL for the image (assuming static serving is handled elsewhere or we return a path)
    # We'll assume a static route exists for uploads.
    base_url = request.host_url.rstrip('/')
    image_url = f"{base_url}/uploads/{saved_filename}" 
    
    return jsonify({
        'success': True, 
        'filepath': filepath, 
        'filename': saved_filename, 
        'image_url': image_url, 
        'dimensions': {'width': width, 'height': height}
    })

@entity_bp.route('/api/ajouter-zone', methods=['POST'])
def ajouter_zone_temp():
    data = request.json
    zone = {
        'id': data.get('id'),
        'nom': data.get('nom'),
        'coords': data.get('coords')
    }
    
    if 'temp_zones' not in session:
        session['temp_zones'] = []
    
    session['temp_zones'].append(zone)
    session.modified = True
    return jsonify({'success': True})

@entity_bp.route('/api/supprimer-zone/<int:zid>', methods=['DELETE'])
def supprimer_zone_temp(zid):
    if 'temp_zones' in session:
        session['temp_zones'] = [z for z in session['temp_zones'] if z['id'] != zid]
        session.modified = True
    return jsonify({'success': True})

@entity_bp.route('/api/detecter-etiquettes', methods=['POST'])
def detecter_etiquettes():
    """
    Détecte automatiquement les positions des étiquettes du cadre de référence via OCR.
    
    Body JSON:
    {
        "filename": "image.jpg",
        "etiquettes": {
            "origine": ["PASSEPORT", "PASSPORT"],
            "largeur": ["P<DZA"],
            "hauteur": ["SIGNATURE"]
        }
    }
    
    Returns:
    {
        "success": true,
        "positions": {
            "origine": {"x": 0.15, "y": 0.08, "found": true, "text": "PASSEPORT"},
            "largeur": {"x": 0.85, "y": 0.92, "found": true, "text": "P<DZA"},
            "hauteur": {"x": 0.12, "y": 0.95, "found": false}
        }
    }
    """
    data = request.json or {}
    filename = data.get('filename')
    etiquettes = data.get('etiquettes', {})
    
    if not filename:
        return jsonify({'error': 'Filename manquant'}), 400
    
    # Construire le chemin de l'image
    image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(image_path):
        return jsonify({'error': f'Image non trouvée: {filename}'}), 404
    
    # Construire la config des ancres à partir des étiquettes
    ancres_config = []
    for etiquette_id, labels in etiquettes.items():
        if labels:  # Si l'utilisateur a fourni des labels
            ancres_config.append({
                'id': etiquette_id,
                'labels': labels if isinstance(labels, list) else [labels]
            })
    
    if not ancres_config:
        return jsonify({'error': 'Aucune étiquette à détecter'}), 400
    
    try:
        # OCR global pour obtenir tous les mots avec positions
        mots_ocr, img_dims = ocr_global_avec_positions(image_path, lang='fra+eng')
        
        if not mots_ocr:
            return jsonify({
                'success': False,
                'error': 'OCR n\'a détecté aucun texte dans l\'image'
            }), 400
        
        # Détecter les étiquettes
        etiquettes_detectees, toutes_trouvees = detecter_ancres(
            mots_ocr, 
            ancres_config, 
            img_dims
        )
        
        # Formater la réponse
        positions = {}
        for etiquette_id in etiquettes.keys():
            if etiquette_id in etiquettes_detectees:
                det = etiquettes_detectees[etiquette_id]
                x = det.get('x', 0)
                y = det.get('y', 0)
                
                # NOUVEAU: Utiliser les bords si disponibles pour plus de précision (AABB)
                if det.get('found') and 'x_min' in det:
                    if etiquette_id == 'haut':
                        # Pour HAUT, utiliser y_min (bord haut) et x centre
                        y = det.get('y_min', y)
                    elif etiquette_id == 'droite':
                        # Pour DROITE, utiliser x_max (bord droit) et y centre
                        x = det.get('x_max', x)
                    elif etiquette_id == 'gauche_bas':
                        # Pour GAUCHE-BAS, utiliser x_min (bord gauche) et y_max (bord bas)
                        x = det.get('x_min', x)
                        y = det.get('y_max', y)
                    elif etiquette_id == 'origine':
                        # Pour ORIGINE (Legacy), utiliser coin haut-gauche
                        x = det.get('x_min', x)
                        y = det.get('y_min', y)

                positions[etiquette_id] = {
                    'x': x,
                    'y': y,
                    'found': det.get('found', False),
                    'text': det.get('text', '')
                }
            else:
                positions[etiquette_id] = {'x': 0, 'y': 0, 'found': False}
        
        return jsonify({
            'success': True,
            'toutes_trouvees': toutes_trouvees,
            'positions': positions,
            'image_dimensions': {'width': img_dims[0], 'height': img_dims[1]}
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entity_bp.route('/api/sauvegarder-entite', methods=['POST'])
def sauvegarder_entite():
    data = request.json
    nom = data.get('nom')
    description = data.get('description', '')
    
    # NOUVEAU: Récupérer le cadre de référence (3 étiquettes)
    cadre_reference = data.get('cadre_reference')
    
    # Angular: Send 'zones' array directly
    zones = data.get('zones') or session.get('temp_zones', [])
    
    # Angular: Send 'image_filename' or 'image_path' if available
    image_path = None
    if data.get('image_filename'):
         image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], data.get('image_filename'))
    else:
         image_path = session.get('temp_image_path')
    
    if not nom: return jsonify({'error': 'Nom manquant'}), 400
    if not zones: return jsonify({'error': 'Aucune zone définie'}), 400

    try:
        get_manager().sauvegarder_entite(nom, zones, image_path=image_path, description=description, cadre_reference=cadre_reference)
        session.pop('temp_zones', None)
        session.pop('temp_image_path', None)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entity_bp.route('/api/entite/<nom>/modifier-zone/<int:zid>', methods=['PUT'])
def modifier_zone_existante(nom, zid):
    manager = get_manager()
    entite = manager.charger_entite(nom)
    if not entite: return jsonify({'error': 'Not found'}), 404
    
    data = request.json
    zones = entite.get('zones', [])
    found = False
    for z in zones:
        if z.get('id') == zid:
            z['nom'] = data['nom']
            z['coords'] = data['coords']
            found = True
            break
            
    if found:
        manager.sauvegarder_entite(entite['nom'], zones, image_path=entite.get('image_reference'), description=entite.get('description', ''))
        return jsonify({'success': True})
    return jsonify({'error': 'Zone not found'}), 404

@entity_bp.route('/api/entite/<nom>/supprimer-zone/<int:zid>', methods=['DELETE'])
def supprimer_zone_existante(nom, zid):
    manager = get_manager()
    entite = manager.charger_entite(nom)
    if not entite: return jsonify({'error': 'Not found'}), 404
    
    zones = [z for z in entite.get('zones', []) if z.get('id') != zid]
    manager.sauvegarder_entite(entite['nom'], zones, image_path=entite.get('image_reference'), description=entite.get('description', ''))
    return jsonify({'success': True})

@entity_bp.route('/api/entite/<nom>', methods=['DELETE'])
def supprimer_entite(nom):
    """Supprime une entité complète"""
    manager = get_manager()
    entite = manager.charger_entite(nom)
    if not entite:
        return jsonify({'error': 'Entity not found'}), 404
    
    try:
        # Supprimer le fichier JSON de l'entité
        entite_path = os.path.join(manager.entities_dir, f"{nom}.json")
        if os.path.exists(entite_path):
            os.remove(entite_path)
        
        # Optionnel : supprimer l'image de référence si elle existe
        if entite.get('image_reference'):
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], entite['image_reference'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

