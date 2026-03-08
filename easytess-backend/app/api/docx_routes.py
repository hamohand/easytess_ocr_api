"""
Routes API pour l'extraction de contenu Word (.docx)
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import uuid
import json

from app.services.docx_extractor import extract_document

docx_bp = Blueprint('docx', __name__)

DOCX_EXTENSIONS = {'.docx'}


@docx_bp.route('/api/extract-docx', methods=['POST'])
def api_extract_docx():
    """
    Extrait le contenu (texte + tableaux) d'un fichier Word.

    Form data:
        file: fichier .docx (obligatoire)
        table_columns: JSON array d'indices de colonnes (optionnel)
                       Ex: "[0, 2]" pour extraire les colonnes 1 et 3
    
    Returns:
        JSON avec le contenu extrait dans l'ordre d'apparition
    """
    # Validation du fichier
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext not in DOCX_EXTENSIONS:
        return jsonify({
            'error': f'Format non supporté: {ext}. Seuls les fichiers .docx sont acceptés.'
        }), 400

    # Sauvegarde temporaire
    unique_id = str(uuid.uuid4())
    saved_filename = f"docx_{unique_id}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)

    try:
        # Parsing des colonnes optionnelles
        table_columns = None
        table_columns_raw = request.form.get('table_columns')
        if table_columns_raw:
            try:
                table_columns = json.loads(table_columns_raw)
                if not isinstance(table_columns, list):
                    return jsonify({
                        'error': 'table_columns doit être un tableau JSON, ex: [0, 2]'
                    }), 400
                table_columns = [int(c) for c in table_columns]
            except (json.JSONDecodeError, ValueError):
                return jsonify({
                    'error': 'table_columns invalide. Format attendu: [0, 2]'
                }), 400

        # Extraction
        content = extract_document(filepath, table_columns=table_columns)

        return jsonify({
            'success': True,
            'filename': filename,
            'total_blocs': len(content),
            'contenu': content
        })

    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500

    finally:
        # Nettoyage du fichier temporaire
        if os.path.exists(filepath):
            os.remove(filepath)
