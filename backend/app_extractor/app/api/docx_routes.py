"""
Routes API pour l'extraction de contenu Word (.docx) — endpoint legacy.
Délègue vers la logique partagée de document_routes.
"""
from flask import Blueprint, request, jsonify

from app.api.document_routes import _save_temp_file, _parse_table_columns, _cleanup
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
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="docx")

        if ext not in DOCX_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. Seuls les fichiers .docx sont acceptés.'
            }), 400

        table_columns = _parse_table_columns(request.form)
        content = extract_document(filepath, table_columns=table_columns)

        return jsonify({
            'success': True,
            'filename': filename,
            'total_blocs': len(content),
            'contenu': content
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)

