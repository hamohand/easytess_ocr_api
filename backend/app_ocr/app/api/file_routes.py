from flask import Blueprint, request, jsonify, session, current_app, send_from_directory, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import json
import logging
from datetime import datetime
from easy_core.pdf_utils import convert_pdf_to_image
from easy_core.image_utils import crop_image

logger = logging.getLogger(__name__)

file_bp = Blueprint('file', __name__)

@file_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())
    saved_filename = f"ocr_{unique_id}_{filename}"
    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    filepath = os.path.join(temp_folder, saved_filename)
    file.save(filepath)
    
    # Conversion PDF -> Image si nécessaire
    if filename.lower().endswith('.pdf'):
        try:
            image_filename = f"{os.path.splitext(saved_filename)[0]}.jpg"
            image_filepath = os.path.join(temp_folder, image_filename)
            convert_pdf_to_image(filepath, image_filepath)
            
            # On bascule sur l'image pour la suite du traitement
            saved_filename = image_filename
            filepath = image_filepath
        except Exception as e:
            return jsonify({'error': f'Erreur lors de la conversion PDF: {str(e)}'}), 500
    
    session['image_path'] = filepath
    session['filename'] = filename
    session['saved_filename'] = saved_filename
    
    return jsonify({
        'success': True, 
        'filename': filename, 
        'saved_filename': saved_filename,
        'url': f"/uploads_temp/{saved_filename}"
    })

@file_bp.route('/api/upload-batch', methods=['POST'])
def upload_batch():
    if 'images' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No selected files'}), 400
    
    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    uploaded = []
    for file in files:
        if file.filename == '':
            continue
        filename = secure_filename(file.filename)
        unique_id = str(uuid.uuid4())
        saved_filename = f"ocr_{unique_id}_{filename}"
        filepath = os.path.join(temp_folder, saved_filename)
        file.save(filepath)
        
        # Conversion PDF -> Image si nécessaire
        if filename.lower().endswith('.pdf'):
            try:
                image_filename = f"{os.path.splitext(saved_filename)[0]}.jpg"
                image_filepath = os.path.join(temp_folder, image_filename)
                convert_pdf_to_image(filepath, image_filepath)
                saved_filename = image_filename
            except Exception as e:
                uploaded.append({
                    'filename': filename,
                    'saved_filename': None,
                    'error': f'Erreur conversion PDF: {str(e)}'
                })
                continue
        
        uploaded.append({
            'filename': filename,
            'saved_filename': saved_filename
        })
    
    return jsonify({
        'success': True,
        'files': uploaded
    })

@file_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve permanent uploaded files (entity references, templates)"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@file_bp.route('/uploads_temp/<path:filename>')
def uploaded_temp_file(filename):
    """Serve temporary uploaded files (OCR sessions)"""
    return send_from_directory(current_app.config['UPLOAD_TEMP_FOLDER'], filename)

@file_bp.route('/api/export-json')
def export_json():
    resultats = session.get('resultats', {})
    export_data = {
        'filename': session.get('filename'),
        'date': datetime.now().isoformat(),
        'resultats': resultats
    }
    return jsonify(export_data)

@file_bp.route('/api/export-json-file', methods=['GET', 'POST'])
def export_json_file():
    if request.method == 'POST':
        data = request.json
        resultats = data.get('resultats', {})
        filename_base = data.get('filename', 'resultats')
    else:
        resultats = session.get('resultats', {})
        filename_base = session.get('filename', 'resultats')

    export_data = {
        'filename': filename_base,
        'date': datetime.now().isoformat(),
        'resultats': resultats
    }
    
    filename = f"export_{filename_base}.json"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
        
    return send_file(filepath, as_attachment=True, download_name=filename)

@file_bp.route('/api/export-json-batch', methods=['POST'])
def export_json_batch():
    data = request.json or {}
    resultats_batch = data.get('resultats_batch', [])
    
    export_data = {
        'date': datetime.now().isoformat(),
        'total': len(resultats_batch),
        'resultats_batch': resultats_batch
    }
    
    filename = f"export_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
        
    return send_file(filepath, as_attachment=True, download_name=filename)


@file_bp.route('/api/crop-image', methods=['POST'])
def crop_image_endpoint():
    """Extrait une partie d'une image selon un cadre défini.

    Accepte soit un fichier uploadé (multipart 'image'), soit le nom
    d'un fichier déjà uploadé (saved_filename). Les coordonnées du
    sommet haut-gauche (x, y) et les dimensions (width, height) sont
    en pixels.

    Form data / JSON:
        image (file, optional): Fichier image à découper.
        saved_filename (str, optional): Nom d'un fichier déjà uploadé.
        x (int): Coordonnée X du sommet haut-gauche.
        y (int): Coordonnée Y du sommet haut-gauche.
        width (int): Largeur du cadre.
        height (int): Hauteur du cadre.
        format (str, optional): Format de sortie ('jpg' ou 'png'). Défaut: 'jpg'.

    Returns:
        L'image découpée en téléchargement.
    """
    # --- Récupérer les paramètres ---
    if request.content_type and 'multipart/form-data' in request.content_type:
        params = request.form
    else:
        params = request.json or {}

    try:
        x = int(params.get('x', -1))
        y = int(params.get('y', -1))
        w = int(params.get('width', -1))
        h = int(params.get('height', -1))
    except (ValueError, TypeError):
        return jsonify({'error': 'x, y, width et height doivent être des entiers'}), 400

    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return jsonify({
            'error': 'Paramètres manquants ou invalides. '
                     'Fournir x, y (≥0) et width, height (>0) en pixels.'
        }), 400

    output_format = params.get('format', 'jpg').lower()
    if output_format not in ('jpg', 'jpeg', 'png'):
        output_format = 'jpg'
    ext = 'jpg' if output_format in ('jpg', 'jpeg') else 'png'
    mimetype = 'image/jpeg' if ext == 'jpg' else 'image/png'

    # --- Résoudre l'image source ---
    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    source_path = None
    cleanup_temp = False

    # Option 1 : fichier uploadé dans la requête
    if 'image' in request.files:
        file = request.files['image']
        if file.filename:
            filename = secure_filename(file.filename)
            unique_id = str(uuid.uuid4())
            saved = f"crop_{unique_id}_{filename}"
            source_path = os.path.join(temp_folder, saved)
            file.save(source_path)
            cleanup_temp = True

    # Option 2 : fichier déjà uploadé (par saved_filename)
    if not source_path:
        saved_filename = params.get('saved_filename', '')
        if saved_filename:
            candidate = os.path.join(temp_folder, saved_filename)
            if os.path.exists(candidate):
                source_path = candidate
            else:
                # Chercher aussi dans uploads permanent
                candidate = os.path.join(
                    current_app.config['UPLOAD_FOLDER'], saved_filename
                )
                if os.path.exists(candidate):
                    source_path = candidate

    if not source_path:
        return jsonify({
            'error': 'Aucune image fournie. Envoyer un fichier (champ "image") '
                     'ou indiquer "saved_filename".'
        }), 400

    # --- Découper ---
    try:
        output_name = f"cropped_{uuid.uuid4().hex[:8]}.{ext}"
        output_path = os.path.join(temp_folder, output_name)

        crop_image(source_path, x, y, w, h, output_path=output_path)

        return send_file(
            output_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=output_name
        )
    except (FileNotFoundError, ValueError, TypeError) as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception("Erreur lors du crop")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500
    finally:
        # Nettoyage du fichier source temporaire (si uploadé pour ce crop)
        if cleanup_temp and source_path and os.path.exists(source_path):
            try:
                os.remove(source_path)
            except OSError:
                pass


@file_bp.route('/api/crop-image-batch', methods=['POST'])
def crop_image_batch_endpoint():
    """Découpe un lot d'images avec les mêmes coordonnées de cadre.

    Accepte plusieurs fichiers images (champ 'images') et les découpe
    tous avec les mêmes paramètres (x, y, width, height).
    Retourne un ZIP contenant toutes les images découpées.

    Form data:
        images (files): Fichiers images à découper.
        x (int): Coordonnée X du sommet haut-gauche.
        y (int): Coordonnée Y du sommet haut-gauche.
        width (int): Largeur du cadre.
        height (int): Hauteur du cadre.
        format (str, optional): Format de sortie ('jpg' ou 'png'). Défaut: 'jpg'.

    Returns:
        ZIP contenant les images découpées.
    """
    import zipfile
    import io

    # --- Récupérer les paramètres ---
    params = request.form

    try:
        x = int(params.get('x', -1))
        y = int(params.get('y', -1))
        w = int(params.get('width', -1))
        h = int(params.get('height', -1))
    except (ValueError, TypeError):
        return jsonify({'error': 'x, y, width et height doivent être des entiers'}), 400

    if x < 0 or y < 0 or w <= 0 or h <= 0:
        return jsonify({
            'error': 'Paramètres manquants ou invalides. '
                     'Fournir x, y (≥0) et width, height (>0) en pixels.'
        }), 400

    files = request.files.getlist('images')
    if not files:
        return jsonify({'error': 'Aucune image fournie (champ "images").'}), 400

    output_format = params.get('format', 'jpg').lower()
    if output_format not in ('jpg', 'jpeg', 'png'):
        output_format = 'jpg'
    ext = 'jpg' if output_format in ('jpg', 'jpeg') else 'png'

    temp_folder = current_app.config['UPLOAD_TEMP_FOLDER']
    temp_files = []

    try:
        # Créer le ZIP en mémoire
        zip_buffer = io.BytesIO()
        results_summary = []

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if not file.filename:
                    continue

                original_name = secure_filename(file.filename)
                base_name = os.path.splitext(original_name)[0]
                temp_src = os.path.join(temp_folder, f"batch_{uuid.uuid4().hex[:8]}_{original_name}")
                file.save(temp_src)
                temp_files.append(temp_src)

                try:
                    output_name = f"{base_name}_crop.{ext}"
                    temp_out = os.path.join(temp_folder, f"crop_{uuid.uuid4().hex[:8]}.{ext}")
                    temp_files.append(temp_out)

                    crop_image(temp_src, x, y, w, h, output_path=temp_out)
                    zf.write(temp_out, output_name)
                    results_summary.append({
                        'filename': original_name,
                        'output': output_name,
                        'success': True
                    })
                except Exception as e:
                    logger.warning(f"Erreur crop pour {original_name}: {e}")
                    results_summary.append({
                        'filename': original_name,
                        'success': False,
                        'error': str(e)
                    })

            # Ajouter un résumé JSON dans le ZIP
            summary = json.dumps({
                'crop_params': {'x': x, 'y': y, 'width': w, 'height': h},
                'format': ext,
                'total': len(results_summary),
                'reussis': sum(1 for r in results_summary if r['success']),
                'resultats': results_summary
            }, ensure_ascii=False, indent=2)
            zf.writestr('_resume_crop.json', summary)

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"crop_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
    except Exception as e:
        logger.exception("Erreur lors du crop batch")
        return jsonify({'error': f'Erreur interne: {str(e)}'}), 500
    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError:
                pass
