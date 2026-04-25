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

from app.services.pdf_extractor import extract_pdf, filter_columns, extract_rows_with_single_tariff_code, normalize_labels
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
    ---
    tags:
      - Extraction
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Fichier PDF à analyser
      - name: table_columns
        in: formData
        type: string
        required: false
        description: 'JSON array d''indices de colonnes. Ex: "[0, 2]"'
      - name: pages
        in: formData
        type: string
        required: false
        description: 'JSON array de numéros de pages (1-based). Ex: "[1, 3]"'
      - name: strategy
        in: formData
        type: string
        required: false
        enum: [auto, standard, text, lines_strict]
        default: auto
        description: Stratégie de détection des tableaux
    responses:
      200:
        description: Contenu extrait avec succès
      400:
        description: Fichier manquant ou format non supporté
      500:
        description: Erreur interne
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
    Extraction unifiée — détecte automatiquement PDF ou DOCX.
    ---
    tags:
      - Extraction
    consumes:
      - multipart/form-data
    parameters:
      - name: file
        in: formData
        type: file
        required: true
        description: Fichier PDF ou DOCX à analyser
      - name: table_columns
        in: formData
        type: string
        required: false
        description: 'JSON array d''indices de colonnes. Ex: "[0, 2]"'
      - name: pages
        in: formData
        type: string
        required: false
        description: 'Pages à traiter (PDF uniquement). Ex: "[1, 3]"'
      - name: strategy
        in: formData
        type: string
        required: false
        enum: [auto, standard, text, lines_strict]
        default: auto
        description: Stratégie de détection (PDF uniquement)
    responses:
      200:
        description: Contenu extrait avec format détecté (pdf ou docx)
      400:
        description: Fichier manquant ou format non supporté
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


# ═════════════════════════════════════════════════════════════
# 4. POST /api/extract-pdf-columns — Extraction filtrée par colonnes
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/extract-pdf-columns', methods=['POST'])
def api_extract_pdf_columns():
    """
    Extrait un PDF et retourne uniquement les colonnes demandées
    des tableaux trouvés.

    Form data:
        file: fichier .pdf (obligatoire)
        columns: JSON array de noms de colonnes (optionnel)
                 Défaut: ["Position & Sous", "Désignation des Produits"]
                 La recherche est partielle et insensible à la casse.
        pages: JSON array de pages 1-based (optionnel)
        strategy: Stratégie de détection tableaux (optionnel)

    Returns:
        JSON avec les lignes filtrées contenant uniquement les colonnes demandées
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="cols")

        if ext not in PDF_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. Seuls les fichiers .pdf sont acceptés.'
            }), 400

        # Colonnes à extraire (défaut: Position & Désignation)
        columns_raw = request.form.get('columns')
        if columns_raw:
            try:
                column_names = json.loads(columns_raw)
                if not isinstance(column_names, list):
                    raise ValueError("Doit être un tableau JSON")
            except (json.JSONDecodeError, ValueError) as e:
                return jsonify({'error': f'columns invalide: {e}'}), 400
        else:
            column_names = ["Position & Sous", "Désignation des Produits"]

        pages = _parse_pages(request.form)
        strategy = request.form.get('strategy', 'auto')

        # 1. Extraction complète du PDF
        content, stats = extract_pdf(
            filepath,
            pages=pages,
            strategy=strategy,
            include_metadata=True
        )

        # 2. Filtrage par colonnes
        filtered = filter_columns(content, column_names)

        return jsonify({
            'success': True,
            'filename': filename,
            'colonnes_demandees': column_names,
            'nb_lignes': len(filtered),
            'lignes': filtered,
            'statistiques': stats,
        })

    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)


# ═════════════════════════════════════════════════════════════
# 5. POST /api/extract-tariff-codes — Extraction dynamique des codes
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/extract-tariff-codes', methods=['POST'])
def api_extract_tariff_codes():
    """
    Extrait un PDF et cherche dynamiquement tous les codes tarifaires
    (format XXXX.XX.XX.XX) quelle que soit la colonne où ils se trouvent.
    Associe chaque code avec la colonne Désignation correspondante.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni (champ "file" requis)'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400

    filepath = None
    try:
        filepath, filename, ext = _save_temp_file(file, prefix="codes")

        if ext not in PDF_EXTENSIONS:
            return jsonify({
                'error': f'Format non supporté: {ext}. Seuls les fichiers .pdf sont acceptés.'
            }), 400

        pages = _parse_pages(request.form)
        strategy = request.form.get('strategy', 'auto')

        # 1. Extraction complète
        content, stats = extract_pdf(
            filepath,
            pages=pages,
            strategy=strategy,
            include_metadata=False
        )

        # 2. Recherche dynamique : lignes contenant exactement UN code tarifaire
        results = extract_rows_with_single_tariff_code(content)

        return jsonify({
            'success': True,
            'filename': filename,
            'nb_lignes_trouvees': len(results),
            'donnees': results
        })

    except Exception as e:
        return jsonify({
            'error': f"Erreur lors de l'extraction: {str(e)}"
        }), 500
    finally:
        _cleanup(filepath)


# ═════════════════════════════════════════════════════════════
# 6. POST /api/normalize-labels — Normalisation des étiquettes
# ═════════════════════════════════════════════════════════════
@document_bp.route('/api/normalize-labels', methods=['POST'])
def api_normalize_labels():
    """
    Normalise les étiquettes d'un tableau de lignes extraites.
    ---
    tags:
      - Normalisation
    consumes:
      - application/json
    parameters:
      - name: mapping
        in: query
        type: string
        required: false
        default: default
        description: 'Nom du fichier de config (sans .json) dans config_labels/. Ex: "default", "chapitre_84"'
      - name: body
        in: body
        required: true
        schema:
          type: array
          items:
            type: object
          example:
            - col_04: "Tracteurs agricoles"
              col_05: "D.D 30%"
    responses:
      200:
        description: Lignes avec clés renommées selon le mapping
      400:
        description: Corps de requête invalide
      500:
        description: Erreur de normalisation
    """
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'error': 'Le corps de la requête doit être un tableau JSON valide (liste de lignes).'}), 400

        mapping_name = request.args.get('mapping', 'default')
        normalized = normalize_labels(data, mapping_name=mapping_name)

        return jsonify({
            'success': True,
            'mapping_utilise': mapping_name,
            'nb_lignes_normalisees': len(normalized),
            'donnees': normalized
        })
    except Exception as e:
        return jsonify({'error': f"Erreur de normalisation: {str(e)}"}), 500


