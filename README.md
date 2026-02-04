# 🚀 EasyTess - Application OCR avec support PDF et QR Code

Application complète d'analyse OCR avec gestion d'entités, support des fichiers PDF et détection de QR codes.

> **🚀 Nouveau ?** Consultez le [Guide de démarrage rapide](./docs/QUICKSTART.md)  
> **📚 Documentation complète** → Voir le dossier [`/docs`](./docs/INDEX.md)

## ✨ Fonctionnalités principales

### 📄 Support multi-formats
- ✅ Images (JPG, PNG, BMP, TIFF, etc.)
- ✅ **PDF**
  - Conversion automatique en image haute qualité (300 DPI)
  - Support pour l'analyse OCR
  - Support pour la création d'entités

### 🔍 Analyse OCR hybride
- **Tesseract** : Moteur principal pour l'arabe et le français
- **EasyOCR** : Moteur de secours pour les zones difficiles
- **QR Code/Barcode** : Détection automatique avec OpenCV
- Détection automatique de la meilleure approche
- Niveau de confiance pour chaque zone

### 🏗️ Gestion des entités
- Création de modèles d'extraction personnalisés
- Définition de zones par dessin ou drag & drop
- **Types de zones** : Texte, QR Code, Code-barres
- Modification et suppression d'entités
- Coordonnées relatives (adaptables à différentes tailles d'images)

### 📊 Résultats détaillés
- Texte extrait par zone
- Contenu des QR codes décodés
- Niveau de confiance
- Moteur utilisé (Tesseract, EasyOCR, OpenCV)
- Alertes pour les zones problématiques
- Export JSON des résultats

## 🏗️ Architecture

```
easytess_api/
├── easytess-backend/          # API Flask
│   ├── app/
│   │   ├── api/              # Routes API
│   │   │   ├── file_routes.py      # Upload et gestion fichiers
│   │   │   ├── ocr_routes.py       # Analyse OCR
│   │   │   └── entity_routes.py    # Gestion entités
│   │   ├── services/         # Logique métier
│   │   │   ├── ocr_engine.py       # Moteurs OCR
│   │   │   └── entity_manager.py   # Gestion entités
│   │   └── utils/            # Utilitaires
│   │       ├── pdf_utils.py        # Conversion PDF (nouveau !)
│   │       └── image_utils.py      # Traitement images
│   ├── entities/             # Stockage entités (JSON)
│   └── uploads/              # Fichiers uploadés
│
├── easytess-frontend/         # Application Angular
│   └── src/app/
│       ├── components/
│       │   ├── ocr-upload.component.*     # Analyse OCR
│       │   └── entity-creator.component.* # Création entités
│       └── services/
│           ├── file.service.ts
│           ├── ocr.service.ts
│           └── entity.service.ts
│
└── docs/
    ├── PDF_SUPPORT.md        # Documentation technique PDF
    └── GUIDE_PDF.md          # Guide utilisateur PDF
```

## 🚀 Installation

### Prérequis
- Python 3.8+
- Node.js 16+
- Tesseract OCR

### Backend

```bash
cd easytess-backend

# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python run.py
```

Le serveur démarre sur `http://localhost:8082`

### Frontend

```bash
cd easytess-frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement
ng serve
```

L'application est accessible sur `http://localhost:4200`

## 📦 Dépendances principales

### Backend
- **Flask** : Framework web
- **Flask-Cors** : Gestion CORS
- **pytesseract** : Interface Python pour Tesseract
- **easyocr** : Moteur OCR alternatif
- **pypdfium2** : Conversion PDF (nouveau !)
- **Pillow** : Traitement d'images
- **opencv-python** : Vision par ordinateur

### Frontend
- **Angular 17+** : Framework frontend
- **TypeScript** : Langage
- **RxJS** : Programmation réactive

## 🎯 Utilisation rapide

### 1. Analyser un document

```typescript
// Depuis l'interface Angular
1. Onglet "OCR Analysis"
2. Sélectionner une entité (ou "Aucun")
3. Uploader une image ou un PDF
4. Cliquer sur "Analyser avec OCR"
5. Consulter les résultats
6. Exporter en JSON si nécessaire
```

### 2. Créer une entité

```typescript
// Depuis l'interface Angular
1. Onglet "Entity Management"
2. Cliquer sur "Créer une nouvelle entité"
3. Nommer l'entité
4. Uploader une image ou un PDF de référence
5. Dessiner les zones d'extraction
6. Nommer chaque zone
7. Sauvegarder
```

## 🔧 Configuration

### Résolution PDF
Par défaut, les PDF sont convertis en 300 DPI. Pour modifier :

```python
# app/utils/pdf_utils.py
def convert_pdf_to_image(pdf_path, output_path=None, dpi=300):
    # Changer la valeur de dpi ici
```

### Langues OCR
Par défaut : Arabe + Français. Pour modifier :

```python
# app/services/ocr_engine.py

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

- [ ] Support multi-pages pour les PDF
- [ ] Choix de la page à convertir
- [ ] Détection de codes-barres avec zbar (actuellement QR codes uniquement)
- [ ] Support de plus de langues OCR
- [ ] API REST complète avec documentation Swagger
- [ ] Batch processing (traitement par lot)
- [ ] Interface de correction manuelle des résultats
- [ ] Historique des analyses
- [ ] Authentification et gestion des utilisateurs

## 📝 Licence

Ce projet est un outil interne de traitement OCR.

## 👥 Contribution

Pour toute question ou suggestion, contactez l'équipe de développement.

---

**Version** : 2.1.0 (avec support PDF et QR Code)  
**Dernière mise à jour** : Janvier 2026
#   e a s y t e s s _ o c r _ a p i  
 