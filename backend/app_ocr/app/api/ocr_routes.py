from flask import Blueprint, request, jsonify, session, current_app, Response
import os
import json
import uuid
import threading
import time
import logging

logger = logging.getLogger(__name__)

from app.services.ocr_engine import analyser_hybride
from app.services.ocr_engine_v2 import analyser_hybride as analyser_hybride_v2
from werkzeug.utils import secure_filename
from easy_core.pdf_utils import convert_pdf_to_image

ocr_bp = Blueprint('ocr', __name__)

# Store for async batch jobs
_batch_jobs = {}
_batch_jobs_lock = threading.Lock()

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

def _resolve_image_path(filename, app=None):
    """Cherche un fichier dans uploads_temp d'abord, puis dans uploads."""
    from flask import current_app as _ca
    ctx = app or _ca
    temp_folder = ctx.config['UPLOAD_TEMP_FOLDER']
    perm_folder = ctx.config['UPLOAD_FOLDER']
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
        
    temp_path = os.path.join(temp_folder, filename)
    if os.path.exists(temp_path):
        return temp_path
    perm_path = os.path.join(perm_folder, filename)
    if os.path.exists(perm_path):
        return perm_path
    return None  # introuvable

def _analyser_un_fichier(image_path, filename, zones_config, cadre_reference, mode='rapide'):
    """Analyse un seul fichier — utilisé par le ThreadPoolExecutor."""
    try:
        resultats, alertes, cadre_detecte = analyser_hybride_v2(image_path, zones_config, cadre_reference=cadre_reference, mode=mode)
        
        if resultats is None:
            return {
                'filename': filename,
                'success': False,
                'error': alertes
            }
        else:
            stats = {}
            for r in resultats.values():
                m = r.get('moteur', 'inconnu')
                stats[m] = stats.get(m, 0) + 1
            return {
                'filename': filename,
                'success': True,
                'resultats': resultats,
                'alertes': alertes,
                'cadre_detecte': cadre_detecte,
                'stats_moteurs': stats
            }
    except Exception as e:
        return {
            'filename': filename,
            'success': False,
            'error': str(e)
        }


@ocr_bp.route('/api/analyser/v1', methods=['POST'])
def api_analyser_v1():
    """
    Analyse un document avec l'ancien moteur OCR (Version 01 - Tesseract pur)
    ---
    tags:
      - OCR Analysis
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            filename:
              type: string
              example: "document_test.jpg"
            mode:
              type: string
              example: "rapide"
    responses:
      200:
        description: Analyse réussie
      400:
        description: Erreur dans les paramètres
    """
    data = request.json or {}
    logger.info(f"Requête OCR V1 reçue: filename={data.get('filename')}, mode={data.get('mode')}")
    filename = data.get('filename')
    
    # 1. Determine Image Path
    image_path = None
    if filename:
        image_path = _resolve_image_path(filename)
    elif 'image_path' in session:
        image_path = session['image_path']
        
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image not found. Please upload first or provide filename.'}), 400
        
    # 2. Determine Entity/Zones
    entite_active = session.get('entite_active')
    
    if data.get('zones'):
        zones_config = data['zones']
    elif data.get('entite'):
        # Charger l'entité depuis le manager si demandée explicitement (très utile pour Swagger)
        entite_nom = data['entite']
        entite_config = current_app.entity_manager.charger_entite(entite_nom)
        if entite_config and 'zones' in entite_config:
            zones_config = {z['nom']: {**z, 'lang': z.get('lang', 'ara+fra'), 'char_filter': z.get('char_filter', 'none')} for z in entite_config['zones']}
        else:
            return jsonify({'error': f"Entité '{entite_nom}' introuvable ou invalide."}), 400
    elif entite_active:
        zones_config = {z['nom']: {**z, 'lang': z.get('lang', 'ara+fra'), 'char_filter': z.get('char_filter', 'none')} for z in entite_active['zones']}
    else:
        zones_config = {"Test": {"coords": [100, 100, 300, 200]}}
    
    cadre_reference = data.get('cadre_reference')
    mode = data.get('mode', 'rapide')
    
    try:
        resultats, alertes, cadre_detecte = analyser_hybride(image_path, zones_config, cadre_reference=cadre_reference, mode=mode)
        
        if resultats is None:
            return jsonify({
                'success': False,
                'error': alertes,
                'error_type': 'etiquettes_non_trouvees'
            }), 400
        
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
            'cadre_detecte': cadre_detecte,
            'stats_moteurs': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/api/analyser', methods=['POST'])
def api_analyser():
    """
    Analyse un document avec le moteur OCR hybride (Version 02 - Défaut avec PaddleOCR)
    ---
    tags:
      - OCR Analysis
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            filename:
              type: string
              example: "document_test.jpg"
            mode:
              type: string
              example: "approfondi"
    responses:
      200:
        description: Analyse réussie
      400:
        description: Erreur dans les paramètres
    """
    data = request.json or {}
    logger.info(f"Requête OCR V2 reçue: filename={data.get('filename')}, mode={data.get('mode')}")
    filename = data.get('filename')
    
    # 1. Determine Image Path
    image_path = None
    if filename:
        image_path = _resolve_image_path(filename)
    elif 'image_path' in session:
        image_path = session['image_path']
        
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image not found. Please upload first or provide filename.'}), 400
        
    # 2. Determine Entity/Zones
    entite_active = session.get('entite_active')
    
    if data.get('zones'):
        zones_config = data['zones']
    elif data.get('entite'):
        # Charger l'entité depuis le manager si demandée explicitement (très utile pour Swagger)
        entite_nom = data['entite']
        entite_config = current_app.entity_manager.charger_entite(entite_nom)
        if entite_config and 'zones' in entite_config:
            zones_config = {z['nom']: {**z, 'lang': z.get('lang', 'ara+fra'), 'char_filter': z.get('char_filter', 'none')} for z in entite_config['zones']}
        else:
            return jsonify({'error': f"Entité '{entite_nom}' introuvable ou invalide."}), 400
    elif entite_active:
        zones_config = {z['nom']: {**z, 'lang': z.get('lang', 'ara+fra'), 'char_filter': z.get('char_filter', 'none')} for z in entite_active['zones']}
    else:
        zones_config = {"Test": {"coords": [100, 100, 300, 200]}}
    
    cadre_reference = data.get('cadre_reference')
    mode = data.get('mode', 'rapide')
    
    try:
        # APPEL A LA VERSION V2 (AVEC PADDLEOCR)
        resultats, alertes, cadre_detecte = analyser_hybride_v2(image_path, zones_config, cadre_reference=cadre_reference, mode=mode)
        
        if resultats is None:
            return jsonify({
                'success': False,
                'error': alertes,
                'error_type': 'etiquettes_non_trouvees'
            }), 400
        
        # On ne sauvegarde pas dans la session pour ne pas perturber la V1
        
        stats = {}
        for r in resultats.values():
            m = r.get('moteur', 'inconnu')
            stats[m] = stats.get(m, 0) + 1
            
        return jsonify({
            'success': True, 
            'resultats': resultats, 
            'alertes': alertes, 
            'cadre_detecte': cadre_detecte,
            'stats_moteurs': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================
# API CNI DÉDIÉE (Extraction directe depuis image)
# =============================================

@ocr_bp.route('/api/v1/extract/cni', methods=['POST'])
def api_extract_cni():
    """
    Extrait les informations d'une CNI (Carte Nationale d'Identité) à partir d'une image ou d'un PDF, en une seule étape.
    """
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'Aucun fichier image/pdf fourni. Utilisez le champ "image".'}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Le fichier est vide.'}), 400
        
    filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    saved_filename = f"cni_direct_{unique_id}_{filename}"
    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    
    os.makedirs(temp_folder, exist_ok=True)
    filepath = os.path.join(temp_folder, saved_filename)
    file.save(filepath)
    
    # 1. Conversion PDF -> Image si nécessaire
    if filename.lower().endswith('.pdf'):
        try:
            image_filename = f"{os.path.splitext(saved_filename)[0]}.jpg"
            image_filepath = os.path.join(temp_folder, image_filename)
            convert_pdf_to_image(filepath, image_filepath)
            
            # On bascule sur l'image pour l'analyse
            saved_filename = image_filename
            filepath = image_filepath
        except Exception as e:
            return jsonify({'success': False, 'error': f'Erreur lors de la conversion du PDF: {str(e)}'}), 500
            
    # 2. Charger la configuration "cni_01" ou l'entité demandée
    entite_nom = request.form.get('entite', 'cni_01')
    entite_config = current_app.entity_manager.charger_entite(entite_nom)
    
    if not entite_config or 'zones' not in entite_config:
        return jsonify({'success': False, 'error': f"L'entité '{entite_nom}' n'est pas configurée correctement."}), 500
        
    zones_config = {z['nom']: {**z, 'lang': z.get('lang', 'ara+fra'), 'char_filter': z.get('char_filter', 'none')} for z in entite_config['zones']}
    
    # 3. Lancer l'analyse OCR (mode approfondi par défaut pour les API directes)
    mode = request.form.get('mode', 'approfondi')
    try:
        resultats, alertes, cadre_detecte = analyser_hybride_v2(filepath, zones_config, mode=mode)
        
        # 4. Formater les données de retour
        if resultats is None:
             return jsonify({
                 'success': False,
                 'error': "Impossible d'extraire les données du document.",
                 'alertes': alertes
             }), 400
             
        extracted_data = {k: v.get('texte_final', '') for k, v in resultats.items()}
        
        # 5. Nettoyage du fichier temporaire (Optionnel mais propre)
        try:
            os.remove(filepath)
            if filename.lower().endswith('.pdf'):
                os.remove(os.path.join(temp_folder, saved_filename.replace('.jpg', '') + filename[-4:]))
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup temp file {filepath}: {cleanup_err}")
            
        return jsonify({
            'success': True,
            'document_type': 'CNI',
            'entite_utilisee': entite_nom,
            'data': extracted_data,
            'alertes': alertes
        })
        
    except Exception as e:
        logger.error(f"Erreur extraction CNI: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================
# BATCH SYNCHRONE (petit nombre de fichiers)
# =============================================

@ocr_bp.route('/api/analyser-batch', methods=['POST'])
def api_analyser_batch():
    data = request.json or {}
    filenames = data.get('filenames', [])
    zones_config = data.get('zones')
    cadre_reference = data.get('cadre_reference')
    mode = data.get('mode', 'rapide')
    
    if not filenames:
        return jsonify({'error': 'No filenames provided'}), 400
    
    upload_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    resultats_batch = []
    reussis = 0
    echoues = 0
    
    for filename in filenames:
        image_path = _resolve_image_path(filename)
        
        if not image_path:
            resultats_batch.append({
                'filename': filename,
                'success': False,
                'error': f'Fichier non trouvé: {filename}'
            })
            echoues += 1
            continue
        
        result = _analyser_un_fichier(image_path, filename, zones_config, cadre_reference, mode=mode)
        resultats_batch.append(result)
        if result['success']:
            reussis += 1
        else:
            echoues += 1
    
    return jsonify({
        'success': True,
        'total': len(filenames),
        'reussis': reussis,
        'echoues': echoues,
        'resultats_batch': resultats_batch
    })


# =============================================
# BATCH ASYNC (grand nombre de fichiers)
# =============================================

@ocr_bp.route('/api/analyser-batch-async', methods=['POST'])
def api_analyser_batch_async():
    """Lance une analyse batch en arrière-plan.
    Traite les fichiers séquentiellement dans un thread unique avec le contexte Flask.
    Retourne immédiatement un job_id pour suivre la progression via SSE."""
    data = request.json or {}
    filenames = data.get('filenames', [])
    zones_config = data.get('zones')
    cadre_reference = data.get('cadre_reference')
    mode = data.get('mode', 'rapide')
    
    if not filenames:
        return jsonify({'error': 'No filenames provided'}), 400
    
    job_id = str(uuid.uuid4())
    app = current_app._get_current_object()
    
    job = {
        'status': 'running',
        'total': len(filenames),
        'completed': 0,
        'reussis': 0,
        'echoues': 0,
        'resultats_batch': [],
        'current_file': ''
    }
    
    with _batch_jobs_lock:
        _batch_jobs[job_id] = job
    
    def run_batch():
        with app.app_context():
            for filename in filenames:
                with _batch_jobs_lock:
                    job['current_file'] = filename
                
                image_path = _resolve_image_path(filename, app)
                if not image_path:
                    with _batch_jobs_lock:
                        job['resultats_batch'].append({
                            'filename': filename,
                            'success': False,
                            'error': f'Fichier non trouvé: {filename}'
                        })
                        job['completed'] += 1
                        job['echoues'] += 1
                    continue
                
                result = _analyser_un_fichier(image_path, filename, zones_config, cadre_reference, mode=mode)
                with _batch_jobs_lock:
                    job['resultats_batch'].append(result)
                    job['completed'] += 1
                    if result['success']:
                        job['reussis'] += 1
                    else:
                        job['echoues'] += 1
            
            with _batch_jobs_lock:
                job['status'] = 'done'
    
    thread = threading.Thread(target=run_batch, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'total': len(filenames)
    })


@ocr_bp.route('/api/batch-progress/<job_id>', methods=['GET'])
def api_batch_progress(job_id):
    """SSE endpoint — envoie la progression en temps réel."""
    def generate():
        while True:
            with _batch_jobs_lock:
                job = _batch_jobs.get(job_id)
            
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            
            payload = {
                'status': job['status'],
                'total': job['total'],
                'completed': job['completed'],
                'reussis': job['reussis'],
                'echoues': job['echoues'],
                'current_file': job['current_file']
            }
            
            if job['status'] == 'done':
                payload['resultats_batch'] = job['resultats_batch']
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                # Nettoyage après livraison
                with _batch_jobs_lock:
                    _batch_jobs.pop(job_id, None)
                break
            
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@ocr_bp.route('/api/batch-result/<job_id>', methods=['GET'])
def api_batch_result(job_id):
    """Polling fallback — retourne l'état courant du job."""
    with _batch_jobs_lock:
        job = _batch_jobs.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    response = {
        'status': job['status'],
        'total': job['total'],
        'completed': job['completed'],
        'reussis': job['reussis'],
        'echoues': job['echoues'],
        'current_file': job['current_file']
    }
    
    if job['status'] == 'done':
        response['resultats_batch'] = job['resultats_batch']
    
    return jsonify(response)


# =============================================
# ANALYSE DE DOSSIER SERVEUR
# =============================================

@ocr_bp.route('/api/analyser-dossier', methods=['POST'])
def api_analyser_dossier():
    """Analyse tous les fichiers image d'un dossier côté serveur.
    Le dossier doit être dans uploads/ ou un chemin absolu autorisé."""
    data = request.json or {}
    dossier_path = data.get('dossier')
    zones_config = data.get('zones')
    cadre_reference = data.get('cadre_reference')
    
    if not dossier_path:
        return jsonify({'error': 'dossier path required'}), 400
    
    # Si chemin relatif, chercher dans uploads/
    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.isabs(dossier_path):
        dossier_path = os.path.join(upload_folder, dossier_path)
    
    if not os.path.isdir(dossier_path):
        return jsonify({'error': f'Dossier non trouvé: {dossier_path}'}), 400
    
    # Lister les fichiers image
    filenames = []
    for f in sorted(os.listdir(dossier_path)):
        ext = os.path.splitext(f)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            filenames.append(f)
    
    if not filenames:
        return jsonify({'error': 'Aucun fichier image trouvé dans le dossier'}), 400
    
    # Lancer en mode async
    job_id = str(uuid.uuid4())
    max_workers = data.get('max_workers', 2)
    app = current_app._get_current_object()
    
    job = {
        'status': 'running',
        'total': len(filenames),
        'completed': 0,
        'reussis': 0,
        'echoues': 0,
        'resultats_batch': [],
        'current_file': ''
    }
    
    with _batch_jobs_lock:
        _batch_jobs[job_id] = job
    
    def run_folder_batch():
        with app.app_context():
            for filename in filenames:
                with _batch_jobs_lock:
                    job['current_file'] = filename
                
                image_path = os.path.join(dossier_path, filename)
                result = _analyser_un_fichier(image_path, filename, zones_config, cadre_reference)
                with _batch_jobs_lock:
                    job['resultats_batch'].append(result)
                    job['completed'] += 1
                    if result['success']:
                        job['reussis'] += 1
                    else:
                        job['echoues'] += 1
            
            with _batch_jobs_lock:
                job['status'] = 'done'
    
    thread = threading.Thread(target=run_folder_batch, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'job_id': job_id,
        'total': len(filenames),
        'filenames': filenames
    })


# =============================================
# RÉSULTATS / CORRECTIONS (existant)
# =============================================

@ocr_bp.route('/api/resultats', methods=['GET', 'POST'])
def api_resultats():
    if request.method == 'POST':
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
    
    return jsonify(session.get('resultats', {}))

@ocr_bp.route('/api/corrections', methods=['GET'])
def api_corrections():
    resultats = session.get('resultats', {})
    alertes = session.get('alertes', [])
    zones_a_corriger = {k: v for k, v in resultats.items() if k in alertes}
    return jsonify(zones_a_corriger)
