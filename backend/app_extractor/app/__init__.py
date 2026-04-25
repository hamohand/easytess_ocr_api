from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger
import os
import logging
from config import Config

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

SWAGGER_TEMPLATE = {
    "info": {
        "title": "EasyTess — Document Extractor API",
        "description": "API d'extraction structurée de documents PDF et Word (.docx).\n\n"
                       "Fonctionnalités : extraction de texte et tableaux, conversion PDF→Word, "
                       "extraction de codes tarifaires, normalisation des étiquettes.",
        "version": "3.2.0",
        "contact": {
            "name": "EasyTess"
        },
        "license": {
            "name": "Propriétaire"
        }
    },
    "basePath": "/",
    "schemes": ["http"],
    "consumes": ["multipart/form-data", "application/json"],
    "produces": ["application/json"],
}

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_TEMP_FOLDER'], exist_ok=True)
    
    # Register Blueprints
    from app.api.file_routes import file_bp
    from app.api.docx_routes import docx_bp
    from app.api.document_routes import document_bp
    
    app.register_blueprint(file_bp)
    app.register_blueprint(docx_bp)
    app.register_blueprint(document_bp)
    
    # ─── Error handlers ───
    @app.errorhandler(413)
    def file_too_large(e):
        max_mb = app.config.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024)
        return jsonify({
            'error': f'Fichier trop volumineux. Taille maximale: {max_mb} Mo.'
        }), 413

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            'error': f'Erreur interne du serveur: {str(e)}'
        }), 500
    
    @app.route('/')
    def index():
        return {
            "message": "Document Extractor API is running",
            "version": "3.2.0",
            "endpoints": {
                "extract_document": "POST /api/extract-document",
                "extract_pdf": "POST /api/extract-pdf",
                "extract_docx": "POST /api/extract-docx",
                "convert_pdf_to_docx": "POST /api/convert-pdf-to-docx",
                "extract_tariff_codes": "POST /api/extract-tariff-codes",
                "normalize_labels": "POST /api/normalize-labels",
            }
        }
    
    return app

