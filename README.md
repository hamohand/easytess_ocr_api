# 🚀 EasyTess - Plateforme OCR & Extraction de Documents

Plateforme complète d'analyse OCR et d'extraction de contenu documentaire. Deux sections principales : **EasyTess-OCR** (analyse OCR avec gestion d'entités) et **Extraction de Documents** (extraction structurée PDF/Word, conversion PDF→DOCX).

> **🚀 Nouveau ?** Consultez le [Guide de démarrage rapide](./docs/QUICKSTART.md)  
> **📚 Documentation complète** → Voir le dossier [`/docs`](./docs/INDEX.md)

## ✨ Fonctionnalités principales

### 🔍 Section EasyTess-OCR
- **Analyse OCR hybride** : Tesseract + EasyOCR avec sélection automatique
- **Support multi-formats** : Images (JPG, PNG, TIFF…) et PDF (conversion auto 300 DPI)
- **QR Code/Barcode** : Détection automatique avec OpenCV
- **Gestion des entités** : Modèles d'extraction personnalisés avec zones dessinées
- **Types de zones** : Texte, QR Code, Code-barres
- **Analyse par lot** : Fichier unique, multi-fichiers, dossier entier avec SSE temps réel
- **Système AABB** : Cadre de référence à 3 ancres (Haut, Droite, Gauche)
- **Export JSON** : Résultats détaillés avec confiance et moteur utilisé

### 📄 Section Extraction de Documents
- **Extraction PDF** : Texte + tableaux via `pdfplumber` avec 4 stratégies de détection
- **Extraction DOCX** : Texte + tableaux (vrais Word + pseudo-tableaux tabulés)
- **Extraction unifiée** : Un endpoint, auto-détection du format (PDF ou DOCX)
- **Conversion PDF → Word** : Reconstruction en `.docx` fidèle (texte, tableaux stylés, sauts de page)
- **Détection d'en-têtes** : Identification automatique des lignes d'en-tête dans les tableaux
- **4 stratégies tableaux** : `auto`, `standard` (bordures), `text` (sans bordures), `lines_strict`
- **Export JSON** : Contenu structuré exportable
- **Drag & drop** : Interface intuitive avec prévisualisation

## 🏗️ Architecture

```text
easytess_api/
├── backend/
│   ├── core_lib/              # Noyau commun Python (pdf_utils, image_utils, etc.)
│   ├── app_ocr/               # API Serveur ciblé OCR (Port 8082)
│   │   ├── app/               # Routes, Services et Config OCR
│   │   └── requirements.txt
│   └── app_extractor/         # API Serveur ciblé Extraction (Port 8083)
│       └── app/               # Routes, Services docx/pdf
│
├── frontend_ocr/              # Application Angular 18 dédiée à l'OCR (Port 4200)
├── frontend_extractor/        # Application Angular 18 dédiée à l'Extraction
│
└── docs/                      # Documentation
```

## 🚀 Installation

### Prérequis
- Python 3.8+
- Node.js 16+
- Tesseract OCR

### 1. Backend OCR

```bash
# S'il n'est pas déjà installé, installez le noyau commun en premier
cd backend/core_lib
pip install -e .

# Ensuite, installez l'environnement OCR et lancez l'API
cd ../app_ocr
pip install -r requirements.txt
python run.py
```

Le serveur démarre sur `http://localhost:8082`

### 2. Frontend OCR

```bash
cd frontend_ocr

# Installer les dépendances
npm install

# Lancer le serveur de développement
ng serve
```

L'application est accessible sur `http://localhost:4200`

## 📦 Dépendances principales

### Backend
- **Flask** + **Flask-Cors** : Framework web avec CORS
- **pytesseract** + **easyocr** : Moteurs OCR
- **pypdfium2** : Conversion PDF → image (pour OCR)
- **pdfplumber** : Extraction contenu PDF (texte + tableaux)
- **python-docx** : Extraction/génération Word
- **Pillow** + **opencv-python** : Traitement d'images
- **pyzbar** : Détection codes-barres (optionnel)

### Frontend
- **Angular 18+** : Framework frontend
- **TypeScript** : Typage statique
- **RxJS** : Programmation réactive

## 🎯 Utilisation rapide

### 1. Analyser un document (OCR)

```
1. Section "EasyTess — OCR" → Onglet "Analyse OCR"
2. Mode "Fichier unique" (par défaut)
3. Sélectionner une entité (ou "Aucun")
4. Uploader une image ou un PDF
5. Cliquer sur "Analyser avec OCR"
6. Consulter les résultats
7. Exporter en JSON si nécessaire
```

### 2. Extraire le contenu d'un document

```
1. Section "Extraction de Documents"
2. Choisir le mode : Extraction Unifiée / PDF / Word
3. Glisser-déposer un fichier PDF ou DOCX
4. Ajuster les options (stratégie, pages, colonnes)
5. Cliquer sur "Extraire le contenu"
6. Consulter les textes et tableaux détectés
7. Exporter en JSON ou convertir en Word
```

### 3. Convertir un PDF en Word

```
1. Section "Extraction de Documents" → Mode "PDF → Word"
2. Déposer un fichier PDF
3. Cliquer sur "Convertir en Word"
4. Le fichier .docx est téléchargé automatiquement
```

### 4. Créer une entité (OCR)

```
1. Section "EasyTess — OCR" → Onglet "Gestion des Entités"
2. Cliquer sur "Créer une nouvelle entité"
3. Nommer, uploader l'image de référence
4. Dessiner les zones, nommer, sauvegarder
```

## 🔧 Configuration

### Résolution PDF
Par défaut, les PDF sont convertis en 300 DPI. Pour modifier :

```python
# easy_core/pdf_utils.py
def convert_pdf_to_image(pdf_path, output_path=None, dpi=300):
    # Changer la valeur de dpi ici
```

### Langues OCR
Par défaut : Arabe + Français. Pour modifier :

```python
# app_ocr/app/services/ocr_engine.py

# Tesseract
texte = pytesseract.image_to_string(zone_img, lang='ara+fra', ...)

# EasyOCR
_easyocr_reader = easyocr.Reader(['ar', 'en'], gpu=False)
```

## 📚 Documentation

Pour la documentation complète, consultez le dossier **[`/docs`](./docs/INDEX.md)**.

### Guides utilisateur
- **[Guide de démarrage rapide](./docs/QUICKSTART.md)** - Installation et premiers pas
- **[Guide PDF](./docs/guides/GUIDE_PDF.md)** - Utilisation des fonctionnalités PDF
- **[Guide QR Code](./docs/guides/QRCODE_SUPPORT.md)** - QR Code et codes-barres
- **[Exemples pratiques](./docs/guides/DEMO_SCENARIOS.md)** - Cas d'usage réels

### Documentation technique
- **[Support PDF](./docs/technical/PDF_SUPPORT.md)** - Documentation technique du support PDF
- **[Installation zbar](./docs/technical/ZBAR_INSTALLATION.md)** - Installation de zbar pour les codes-barres
- **[Changelog](./docs/CHANGELOG.md)** - Historique des versions et modifications

## 🐛 Dépannage

### Le serveur backend ne démarre pas
```bash
# Vérifier que toutes les dépendances sont installées
pip install -r requirements.txt

# Vérifier que Tesseract est installé
tesseract --version
```

### Erreur de conversion PDF
```bash
# Réinstaller pypdfium2
pip uninstall pypdfium2
pip install pypdfium2
```

### L'OCR ne détecte rien
- Vérifiez la qualité de l'image/PDF
- Assurez-vous que les zones sont bien définies
- Vérifiez que Tesseract est correctement installé

## 🔄 Workflow typique

1. **Créer une entité** pour un type de document (ex: CNI algérienne)
2. **Définir les zones** d'intérêt (nom, prénom, date de naissance, etc.)
3. **Analyser des documents** du même type en utilisant l'entité créée
4. **Exporter les résultats** en JSON pour traitement ultérieur

## 🎨 Fonctionnalités avancées

### Coordonnées relatives
Les zones sont stockées en coordonnées relatives (0.0 à 1.0), ce qui permet :
- Adaptation automatique à différentes tailles d'images
- Réutilisation des entités sur des documents de résolutions variées

### Analyse hybride
Le système utilise automatiquement :
1. **Tesseract** en premier
2. **EasyOCR** pour les zones avec faible confiance
3. Sélection du meilleur résultat

### Gestion des erreurs
- Alertes pour les zones problématiques
- Statistiques par moteur
- Possibilité de correction manuelle

## 📈 Améliorations futures

- [x] ~~Batch processing (traitement par lot)~~ ✅ v2.4.0
- [x] ~~Extraction de contenu PDF/DOCX~~ ✅ v2.5.0
- [x] ~~Conversion PDF → Word~~ ✅ v2.5.0
- [x] ~~Détection avancée des tableaux~~ ✅ v2.5.0
- [x] **Séparation de l'architecture backend/frontend** ✅ v3.0.0
- [ ] Support multi-pages complet pour l'OCR (actuellement 1ère page uniquement)
- [ ] Détection de codes-barres avec zbar
- [ ] Support de plus de langues OCR
- [ ] API REST complète avec documentation Swagger

## 📝 Licence

Ce projet est un outil interne de traitement OCR.

## 👥 Contribution

Pour toute question ou suggestion, contactez l'équipe de développement.

---

**Version** : 3.0.0 (Scission Monorepo des applications OCR et Extraction)  
**Dernière mise à jour** : Avril 2026