from flask import Blueprint, request, jsonify, session, current_app, url_for
from werkzeug.utils import secure_filename
import os
import uuid
from PIL import Image
from app.utils.pdf_utils import convert_pdf_to_image
from app.services.ocr_engine import ocr_global_avec_positions, detecter_ancres
from app.services.image_matcher import extract_and_save_template

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
    temp_files_to_cleanup = []

    for etiquette_id, config in etiquettes.items():
        # Support both simple list of strings and object with labels/template_coords
        labels = []
        template_coords = None

        if isinstance(config, list):
            labels = config
            offset_x = 0
            offset_y = 0
        elif isinstance(config, dict):
            labels = config.get('labels', [])
            template_coords = config.get('template_coords')
            try:
                offset_x = float(config.get('offset_x', 0))
            except (ValueError, TypeError):
                offset_x = 0.0
                
            try:
                offset_y = float(config.get('offset_y', 0))
            except (ValueError, TypeError):
                offset_y = 0.0
        
        anchor_conf = {
            'id': etiquette_id,
            'labels': labels,
            'offset_x': offset_x,
            'offset_y': offset_y
        }
        
        # Gestion des templates image temporaires pour la détection
        if template_coords and len(template_coords) == 4 and image_path and os.path.exists(image_path):
            try:
                temp_filename = f"temp_template_{uuid.uuid4()}_{etiquette_id}.png"
                temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], temp_filename)
                
                if extract_and_save_template(image_path, template_coords, temp_path):
                    anchor_conf['template_path'] = temp_filename # Relatif pour compatibilité
                    anchor_conf['template_path_abs'] = temp_path # Absolu pour usage direct
                    temp_files_to_cleanup.append(temp_path)
                    current_app.logger.info(f"📷 Template temporaire créé pour {etiquette_id}: {temp_path}")
            except Exception as e:
                current_app.logger.error(f"❌ Erreur extraction template temporaire: {e}")

        ancres_config.append(anchor_conf)
    
    if not ancres_config:
        return jsonify({'error': 'Aucune étiquette à détecter'}), 400
    
    try:
        # OCR global pour obtenir tous les mots avec positions
        mots_ocr, img_dims = ocr_global_avec_positions(image_path, lang='fra+eng')

        # NOTE: Si l'OCR échoue (pas de texte), mots_ocr peut être vide. 
        # Mais on doit quand même continuer si on a des templates images.
        if not mots_ocr and not any('template_path' in a for a in ancres_config):
             return jsonify({
                'success': False,
                'error': 'OCR n\'a détecté aucun texte dans l\'image et aucun template image défini'
            }), 400
        
        if not mots_ocr:
             mots_ocr = [] # Ensure list if None
             # Need img_dims if not returned by OCR
             if not img_dims:
                 img = Image.open(image_path)
                 img_dims = img.size

        # Détecter les étiquettes (Now passing image_path for template matching)
        etiquettes_detectees, toutes_trouvees = detecter_ancres(
            mots_ocr, 
            ancres_config, 
            img_dims,
            image_path=image_path 
        )

        # Cleanup temp files
        for f in temp_files_to_cleanup:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        
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
                    elif etiquette_id == 'gauche':
                        # NEW: Pour GAUCHE (4-anchor system), utiliser x_min (bord gauche) et y centre
                        x = det.get('x_min', x)
                    elif etiquette_id == 'bas':
                        # NEW: Pour BAS (4-anchor system), utiliser y_max (bord bas) et x centre
                        y = det.get('y_max', y)
                    elif etiquette_id == 'gauche_bas':
                        # Pour GAUCHE-BAS (legacy 3-anchor system), utiliser x_min (bord gauche) et y_max (bord bas)
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
                    'text': det.get('text', ''),
                    'bbox': [det.get('x_min'), det.get('y_min'), det.get('x_max'), det.get('y_max')] if det.get('found') and 'x_min' in det else None
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

    # NOUVEAU: Extraire et sauvegarder les templates d'ancres image si définis
    if cadre_reference and image_path and os.path.exists(image_path):
        templates_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'templates', nom)
        
        for anchor_type in ['haut', 'droite', 'gauche', 'bas']:
            anchor = cadre_reference.get(anchor_type, {})
            template_coords = anchor.get('template_coords')
            
            if template_coords and len(template_coords) == 4:
                template_filename = f"{anchor_type}_template.png"
                template_path = os.path.join(templates_dir, template_filename)
                
                if extract_and_save_template(image_path, template_coords, template_path):
                    # Stocker le chemin relatif du template dans le cadre_reference
                    cadre_reference[anchor_type]['template_path'] = f"templates/{nom}/{template_filename}"
                    current_app.logger.info(f"✅ Template {anchor_type} sauvegardé: {template_path}")

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

