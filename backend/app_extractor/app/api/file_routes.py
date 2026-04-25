"""
Routes de gestion des fichiers pour le module Extractor.
Fournit uniquement le serving des fichiers uploadés (permanents et temporaires).
"""
from flask import Blueprint, current_app, send_from_directory

file_bp = Blueprint('file', __name__)


@file_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve permanent uploaded files (converted documents, etc.)"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@file_bp.route('/uploads_temp/<path:filename>')
def uploaded_temp_file(filename):
    """Serve temporary uploaded files (extraction sessions)"""
    return send_from_directory(current_app.config['UPLOAD_TEMP_FOLDER'], filename)
