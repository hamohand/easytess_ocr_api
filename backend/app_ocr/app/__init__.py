from flask import Flask
from flask_cors import CORS
import os
import logging
from config import Config
from flasgger import Swagger

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', force=True)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Swagger UI Configuration
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec',
                "route": '/apispec.json',
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/swagger-ui.html"
    }
    
    template = {
        "swagger": "2.0",
        "info": {
            "title": "API OCR EasyTess",
            "description": "Microservice d'analyse et d'extraction de documents OCR",
            "version": "1.0.0"
        }
    }
    
    Swagger(app, config=swagger_config, template=template)
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_TEMP_FOLDER'], exist_ok=True)
    entities_folder = app.config['ENTITIES_FOLDER']
    os.makedirs(entities_folder, exist_ok=True)
    
    # Initialize Services
    from app.services.entity_manager import EntityManager
    app.entity_manager = EntityManager(entities_folder)
    
    # Register Blueprints
    from app.api.ocr_routes import ocr_bp
    from app.api.entity_routes import entity_bp
    from app.api.file_routes import file_bp
    from app.api.optimizer_routes import optimizer_bp
    from app.api.invoice_routes import invoice_bp
    
    app.register_blueprint(ocr_bp)
    app.register_blueprint(entity_bp)
    app.register_blueprint(file_bp)
    app.register_blueprint(optimizer_bp)
    app.register_blueprint(invoice_bp)
    
    @app.route('/')
    def index():
        return {
            "message": "EasyTess API is running",
            "endpoints": {
                "ocr": "/api/analyser",
                "entities": "/api/entites",
                "upload": "/api/upload"
            }
        }
    
    return app
