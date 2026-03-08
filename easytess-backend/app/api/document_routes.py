"""
Routes API unifiées pour l'extraction de documents (PDF + Word)
et la conversion PDF → Word.

Endpoints:
  POST /api/extract-pdf       — Extraction PDF (texte + tableaux)
  POST /api/extract-document   — Extraction unifiée PDF ou DOCX
  POST /api/convert-pdf-to-docx — Conversion PDF vers Word
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import os
import uuid
import json

from app.services.pdf_extractor import extract_pdf
from app.services.docx_extractor import extract_document
from app.services.pdf_to_docx import convert_pdf_to_docx, convert_content_to_docx

document_bp = Blueprint('document', __name__)

ALLOWED_EXTENSIONS = {'.pdf', '.docx'}
PDF_EXTENSIONS = {'.pdf'}
DOCX_EXTENSIONS = {'.docx'}


def _save_temp_file(file, prefix="doc"):
    """Sauvegarde un fichier uploadé dans le dossier temporaire."""
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    unique_id = str(uuid.uuid4())
    saved_filename = f"{prefix}_{unique_id}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(filepath)
    return filepath, filename, ext


def _parse_table_columns(form):
    """Parse le paramètre table_columns depuis le formulaire."""
    table_columns_raw = form.get('table_columns')
    if not table_columns_raw:
        return None

    try:
        table_columns = json.loads(table_columns_raw)
        if not isinstance(table_columns, list):
            raise ValueError("Doit être un tableau JSON")
        return [int(c) for c in table_columns]
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"table_columns invalide: {e}. Format attendu: [0, 2]")


def _parse_pages(form):
    """Parse le paramètre pages depuis le formulaire."""
    pages_raw = form.get('pages')
    if not pages_raw:
        return None

    try:
        pages = json.loads(pages_raw)
        if not isinstance(pages, list):
            raise ValueError("Doit être un tableau JSON")
        return [int(p) for p in pages]
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"pages invalide: {e}. Format attendu: [1, 2, 3]")


def _cleanup(filepath):
    """Supprime un fichier temporaire."""
    try:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════
# 1. POST /api/extract-pdf — Extraction PDF
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/extract-pdf', methods=['POST'])
def api_extract_pdf():
    """
    Extrait le contenu (texte + tableaux) d'un fichier PDF.

    Form data:
        file: fichier .pdf (obligatoire)
        table_columns: JSON array d'indices de colonnes (optionnel)
                       Ex: "[0, 2]" pour les colonnes 1 et 3
        pages: JSON array de numéros de pages 1-based (optionnel)
               Ex: "[1, 3]" pour pages 1 et 3
        strategy: Stratégie de détection des tableaux (optionnel)
                  "standard" | "text" | "lines_strict" | "auto" (défaut)

    Returns:
        JSON avec le contenu extrait structuré
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="pdf")

        if ext not in PDF_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. Seuls les fichiers .pdf sont acceptés.'
            }), 400

        table_columns = _parse_table_columns(request.form)
        pages = _parse_pages(request.form)
        strategy = request.form.get('strategy', 'auto')

        content, stats = extract_pdf(
            filepath,
            table_columns=table_columns,
            pages=pages,
            strategy=strategy,
            include_metadata=True
        )

        return jsonify({
            'success': True,
            'filename': filename,
            'total_blocs': len(content),
            'contenu': content,
            'statistiques': stats,
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)


# ═════════════════════════════════════════════════════════════
# 2. POST /api/extract-document — Extraction unifiée
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/extract-document', methods=['POST'])
def api_extract_document():
    """
    Extrait le contenu (texte + tableaux) d'un fichier PDF ou Word.
    Détecte automatiquement le format et utilise le bon extracteur.

    Form data:
        file: fichier .pdf ou .docx (obligatoire)
        table_columns: JSON array d'indices de colonnes (optionnel)
        pages: JSON array de pages (optionnel, PDF uniquement)
        strategy: Stratégie de détection tableaux (optionnel, PDF uniquement)

    Returns:
        JSON avec le contenu extrait structuré
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="doc")

        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. '
                         f'Formats acceptés: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        table_columns = _parse_table_columns(request.form)

        if ext in PDF_EXTENSIONS:
            # ─── Extraction PDF ───
            pages = _parse_pages(request.form)
            strategy = request.form.get('strategy', 'auto')

            content, stats = extract_pdf(
                filepath,
                table_columns=table_columns,
                pages=pages,
                strategy=strategy,
                include_metadata=True
            )

            return jsonify({
                'success': True,
                'filename': filename,
                'format': 'pdf',
                'total_blocs': len(content),
                'contenu': content,
                'statistiques': stats,
            })

        elif ext in DOCX_EXTENSIONS:
            # ─── Extraction Word ───
            content = extract_document(filepath, table_columns=table_columns)

            return jsonify({
                'success': True,
                'filename': filename,
                'format': 'docx',
                'total_blocs': len(content),
                'contenu': content,
            })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)


# ═════════════════════════════════════════════════════════════
# 3. POST /api/convert-pdf-to-docx — Conversion PDF → Word
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/convert-pdf-to-docx', methods=['POST'])
def api_convert_pdf_to_docx():
    """
    Convertit un fichier PDF en document Word (.docx).
    Le contenu est extrait puis reconstruit en Word.

    Form data:
        file: fichier .pdf (obligatoire)
        table_columns: JSON array d'indices de colonnes (optionnel)
        pages: JSON array de pages (optionnel)
        strategy: Stratégie de détection tableaux (optionnel)
        download: "true" pour télécharger le fichier directement (optionnel)

    Returns:
        - Si download=true : fichier .docx en téléchargement
        - Sinon : JSON avec le chemin et les statistiques
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    output_path = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="convert")

        if ext not in PDF_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. Seuls les fichiers .pdf sont acceptés.'
            }), 400

        table_columns = _parse_table_columns(request.form)
        pages = _parse_pages(request.form)
        strategy = request.form.get('strategy', 'auto')
        download = request.form.get('download', 'true').lower() == 'true'

        # Extraction du PDF
        content, stats = extract_pdf(
            filepath,
            table_columns=table_columns,
            pages=pages,
            strategy=strategy,
            include_metadata=True
        )

        if not content:
            return jsonify({
                'error': 'Aucun contenu extractible trouvé dans le PDF'
            }), 400

        # Conversion en DOCX
        docx_filename = os.path.splitext(filename)[0] + '.docx'
        output_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            f"converted_{uuid.uuid4()}_{docx_filename}"
        )

        convert_content_to_docx(
            content, output_path,
            source_filename=filename
        )

        if download:
            # Téléchargement direct
            response = send_file(
                output_path,
                as_attachment=True,
                download_name=docx_filename,
                mimetype='application/vnd.openxmlformats-officedocument'
                         '.wordprocessingml.document'
            )
            # Nettoyage après envoi
            @response.call_on_close
            def cleanup_after_send():
                _cleanup(filepath)
                _cleanup(output_path)

            return response
        else:
            # Retourner le JSON avec les stats
            return jsonify({
                'success': True,
                'filename_source': filename,
                'filename_docx': docx_filename,
                'statistiques': stats,
                'message': 'Conversion réussie'
            })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de la conversion: {str(e)}"
        }), 500
    finally:
        if not (request.form.get('download', 'true').lower() == 'true'):
            _cleanup(filepath)
            _cleanup(output_path)
