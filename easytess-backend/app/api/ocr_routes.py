from flask import Blueprint, request, jsonify, session, current_app
import os
from app.services.ocr_engine import analyser_hybride

ocr_bp = Blueprint('ocr', __name__)

@ocr_bp.route('/api/analyser', methods=['POST'])
def api_analyser():
    data = request.json or {}
    print(f"DEBUG: /api/analyser received data: {data}")
    filename = data.get('filename')
    
    # 1. Determine Image Path
    image_path = None
    if filename:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    elif 'image_path' in session:
        image_path = session['image_path']
        
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image not found. Please upload first or provide filename.'}), 400
        
    # 2. Determine Entity/Zones
    # Angular can send specific zones config directly, or an entity name
    entite_active = session.get('entite_active') # Keep session for now, or accept 'entity_name' in body
    
    if data.get('zones'):
        # Direct zones provided by Angular
        zones_config = data['zones']
    elif entite_active:
        zones_config = {z['nom']: {'coords': z['coords']} for z in entite_active['zones']}
    else:
        # Default test zone
        zones_config = {"Test": {"coords": [100, 100, 300, 200]}}
    
    # 3. NOUVEAU: Récupérer le cadre de référence si fourni
    cadre_reference = data.get('cadre_reference')
    
    try:
        resultats, alertes = analyser_hybride(image_path, zones_config, cadre_reference=cadre_reference)
        
        # Gestion de l'erreur d'étiquettes non trouvées
        if resultats is None:
            # alertes contient le message d'erreur
            return jsonify({
                'success': False,
                'error': alertes,
                'error_type': 'etiquettes_non_trouvees'
            }), 400
        
        # We still store in session for the 'resultats' endpoint if used, but return full data for Angular
        session['resultats'] = resultats
        session['alertes'] = alertes
        
        stats = {}
        for r in resultats.values():
            m = r.get('moteur', 'inconnu')
            stats[m] = stats.get(m, 0) + 1
            
        return jsonify({
            'success': True, 
            'resultats': resultats, 
            'alertes': alertes, 
            'stats_moteurs': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ocr_bp.route('/api/resultats', methods=['GET', 'POST'])
def api_resultats():
    if request.method == 'POST':
        # Save corrections
        data = request.json
        resultats = session.get('resultats', {})
        
        for key, value in data.items():
            if key in resultats:
                resultats[key]['texte_final'] = value
                resultats[key]['texte_corrige_manuel'] = value
                resultats[key]['statut'] = 'corrigé'
        
        session['resultats'] = resultats
        session.modified = True
        return jsonify({'success': True})
    
    # GET: Return current results
    return jsonify(session.get('resultats', {}))

@ocr_bp.route('/api/corrections', methods=['GET'])
def api_corrections():
    resultats = session.get('resultats', {})
    alertes = session.get('alertes', [])
    zones_a_corriger = {k: v for k, v in resultats.items() if k in alertes}
    return jsonify(zones_a_corriger)
