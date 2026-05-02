"""
Routes API pour l'extraction de factures.

Endpoints:
  POST /api/extraire-facture       — Extraction d'une facture (image ou PDF)
  POST /api/extraire-facture-batch  — Extraction batch de factures
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime

from app.services.invoice_extractor import extraire_facture, extraire_facture_depuis_pdf
from easy_core.pdf_utils import convert_pdf_to_image

invoice_bp = Blueprint('invoice', __name__)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.pdf'}
PDF_EXTENSIONS = {'.pdf'}


def _save_temp_file(file, prefix="inv"):
    """Sauvegarde un fichier uploadé dans le dossier temporaire."""
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    unique_id = str(uuid.uuid4())
    saved_filename = f"{prefix}_{unique_id}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_TEMP_FOLDER'], saved_filename)
    file.save(filepath)
    return filepath, filename, ext


def _cleanup(filepath):
    """Supprime un fichier temporaire."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════
# POST /api/extraire-facture — Extraction d'une facture
# ═════════════════════════════════════════════════════════════
@invoice_bp.route('/api/extraire-facture', methods=['POST'])
def api_extraire_facture():
    """
    Extrait la liste des articles (désignations) d'une facture.

    Accepte une image (JPG, PNG, TIFF, etc.) ou un PDF.
    Pour les PDF, chaque page est convertie en image puis analysée.

    Form data:
        file: Fichier image ou PDF de la facture (obligatoire)
        lang: Langue OCR (optionnel, défaut: "fra")
              Valeurs: "fra", "ara+fra", "eng"
    
    Returns:
        JSON avec les articles extraits
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    image_path = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="inv")

        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. '
                         f'Formats acceptés: {", ".join(sorted(ALLOWED_EXTENSIONS))}'
            }), 400

        lang = request.form.get('lang', 'fra')

        if ext in PDF_EXTENSIONS:
            # Extraction PDF multi-pages
            result = extraire_facture_depuis_pdf(filepath, lang=lang)
        else:
            # Extraction image directe
            result = extraire_facture(filepath, lang=lang)

        return jsonify({
            'success': result.get('success', False),
            'filename': filename,
            'articles': result.get('articles', []),
            'nb_articles': result.get('nb_articles', 0),
            'en_tete_detecte': result.get('en_tete_detecte'),
            'colonne_designation': result.get('colonne_designation'),
            'total_mots_ocr': result.get('total_mots_ocr', 0),
            'total_lignes': result.get('total_lignes', 0),
            'image_dimensions': result.get('image_dimensions'),
            'nb_pages': result.get('nb_pages'),
            'pages': result.get('pages'),
            'error': result.get('error'),
            'debug': result.get('debug'),
        })

    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)
        _cleanup(image_path)


# ═════════════════════════════════════════════════════════════
# POST /api/extraire-facture-batch — Extraction batch
# ═════════════════════════════════════════════════════════════
@invoice_bp.route('/api/extraire-facture-batch', methods=['POST'])
def api_extraire_facture_batch():
    """
    Extrait les articles de plusieurs factures en un seul appel.

    Form data:
        files: Fichiers image ou PDF (multipart/form-data, champ "files")
        lang: Langue OCR (optionnel, défaut: "fra")
    
    Returns:
        JSON avec les résultats par fichier
    """
    if 'files' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "files" requis)'}), 400

    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    lang = request.form.get('lang', 'fra')
    resultats = []
    total_articles = 0
    temp_files = []

    for file in files:
        if file.filename == '':
            continue

        filepath = None
        try:
            filepath, filename, ext = _save_temp_file(file, prefix="inv_batch")
            temp_files.append(filepath)

            if ext not in ALLOWED_EXTENSIONS:
                resultats.append({
                    'filename': filename,
                    'success': False,
                    'error': f'Format non supporté: {ext}',
                    'articles': [],
                    'nb_articles': 0,
                })
                continue

            if ext in PDF_EXTENSIONS:
                result = extraire_facture_depuis_pdf(filepath, lang=lang)
            else:
                result = extraire_facture(filepath, lang=lang)

            nb = result.get('nb_articles', 0)
            total_articles += nb

            resultats.append({
                'filename': filename,
                'success': result.get('success', False),
                'articles': result.get('articles', []),
                'nb_articles': nb,
                'en_tete_detecte': result.get('en_tete_detecte'),
                'error': result.get('error'),
            })

        except Exception as e:
            resultats.append({
                'filename': file.filename,
                'success': False,
                'error': str(e),
                'articles': [],
                'nb_articles': 0,
            })

    # Nettoyage
    for fp in temp_files:
        _cleanup(fp)

    return jsonify({
        'success': True,
        'total_fichiers': len(resultats),
        'total_articles': total_articles,
        'resultats': resultats,
    })


# ═════════════════════════════════════════════════════════════
# POST /api/export-facture-json — Export JSON des articles
# ═════════════════════════════════════════════════════════════
@invoice_bp.route('/api/export-facture-json', methods=['POST'])
def api_export_facture_json():
    """
    Exporte les résultats d'extraction de facture en fichier JSON téléchargeable.

    Body JSON:
        articles: Liste d'articles à exporter
        filename: Nom du fichier source (optionnel)
    """
    data = request.get_json()
    if not data or 'articles' not in data:
        return jsonify({'error': 'Données manquantes (champ "articles" requis)'}), 400

    export_data = {
        'date_extraction': datetime.now().isoformat(),
        'filename_source': data.get('filename', 'facture'),
        'nb_articles': len(data['articles']),
        'articles': data['articles'],
    }

    filename = f"facture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(current_app.config['UPLOAD_TEMP_FOLDER'], filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    return send_file(filepath, as_attachment=True, download_name=filename)
