FROM python:3.10-slim-bookworm

WORKDIR /app

# ========================================
# ÉTAPE 1: Installer les dépendances de compilation pour Tesseract 5.5.0
# ========================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    wget \
    # Dépendances Leptonica
    libpng-dev \
    libjpeg-dev \
    libtiff-dev \
    libgif-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    zlib1g-dev \
    # Autres dépendances Tesseract
    libicu-dev \
    libpango1.0-dev \
    libcairo2-dev \
    # Dépendances runtime
    libgl1 \
    libglib2.0-0 \
    libzbar0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ========================================
# ÉTAPE 2: Compiler Leptonica 1.85.0 (requis pour Tesseract 5.5)
# ========================================
WORKDIR /tmp
RUN wget https://github.com/DanBloomberg/leptonica/releases/download/1.85.0/leptonica-1.85.0.tar.gz \
    && tar -xzf leptonica-1.85.0.tar.gz \
    && cd leptonica-1.85.0 \
    && mkdir build && cd build \
    && cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && cd /tmp && rm -rf leptonica-*

# ========================================
# ÉTAPE 3: Compiler Tesseract 5.5.0
# ========================================
RUN wget https://github.com/tesseract-ocr/tesseract/archive/refs/tags/5.5.0.tar.gz \
    && tar -xzf 5.5.0.tar.gz \
    && cd tesseract-5.5.0 \
    && mkdir build && cd build \
    && cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && cd /tmp && rm -rf tesseract-* 5.5.0.tar.gz

# ========================================
# ÉTAPE 4: Télécharger les données de langues (arabe + français)
# Utilise tessdata STANDARD (même que Windows) au lieu de tessdata_best
# ========================================
RUN mkdir -p /usr/local/share/tessdata \
    && wget -O /usr/local/share/tessdata/ara.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata \
    && wget -O /usr/local/share/tessdata/fra.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata \
    && wget -O /usr/local/share/tessdata/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata \
    && wget -O /usr/local/share/tessdata/osd.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata

# Variable d'environnement pour Tesseract
ENV TESSDATA_PREFIX=/usr/local/share/tessdata

# ========================================
# ÉTAPE 5: Nettoyer les outils de compilation (réduire taille image)
# ========================================
RUN apt-get update && apt-get remove -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# ========================================
# ÉTAPE 6: Application Python
# ========================================
WORKDIR /app

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p uploads entities

# Variables d'environnement
ENV PORT=8082
ENV PYTHONUNBUFFERED=1

# Exposer le port
EXPOSE 8082

# Healthcheck simple
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/ || exit 1

# Lancer l'application
CMD ["python", "run.py"]
