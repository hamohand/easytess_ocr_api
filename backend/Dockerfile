FROM python:3.10-slim

# Installe les dépendances système nécessaires pour l'OCR, OpenCV, et Zbar
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ara \
    tesseract-ocr-fra \
    libgl1 \
    libzbar0 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie et installe la racine (core_lib)
COPY core_lib /app/core_lib
RUN pip install --no-cache-dir -e /app/core_lib

# Copie et installe les prérequis spécifiques à l'OCR
COPY app_ocr/requirements.txt /app/app_ocr/
RUN pip install --no-cache-dir -r /app/app_ocr/requirements.txt

# Initialiser le cache Pytorch pour eviter des téléchargements excessifs
# (Optionnel: RUN python -c "import easyocr; easyocr.Reader(['ar', 'fr'])" si voulu)

# Copie tout le code de l'application OCR
COPY app_ocr /app/app_ocr

# Navigue dans le répertoire de l'api OCR
WORKDIR /app/app_ocr

# Variables d'environnements
ENV PYTHONUNBUFFERED=1
ENV PORT=8082

EXPOSE 8082

# Démarrage
CMD ["python", "run.py"]
