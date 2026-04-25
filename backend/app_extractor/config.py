import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev_secret_key'
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')          # Fichiers permanents (documents convertis)
    UPLOAD_TEMP_FOLDER = os.path.join(BASE_DIR, 'uploads_temp') # Fichiers temporaires (extraction)
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}
    
    # Limite de taille des fichiers uploadés (50 Mo)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
