# Changelog - EasyTess OCR

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [2.3.0] - 2026-01-31

### 🎉 Ajouts majeurs

#### Nouveau Système de Cadre de Référence (AABB)
- **3 Ancres** : Définition du cadre par `Haut`, `Droite`, `Gauche-Bas` (au lieu de Origine/Largeur/Hauteur).
- **Robustesse** : Permet de gérer les images décalées, redimensionnées ou avec des marges différentes.
- **Métriques Absolues** : Calcul et stockage des dimensions réelles en pixels et de l'angle.

#### Moteur OCR : Rognage Physique (Physical Crop)
- **Pipeline Strict** : L'image est physiquement rognée selon le cadre détecté avant toute analyse OCR.
- **Isolation** : Garantit que les éléments hors-cadre (bords de table, bruit) ne perturbent pas l'extraction.
- **Re-mapping Coordonnées** : Les résultats de l'analyse rognée sont automatiquement reconvertis dans le repère de l'image originale pour l'affichage.

### 🔧 Modifications techniques

#### Backend (`ocr_engine.py`)
- Fonction `detecter_ancres` améliorée :
  - Support de l'inclusion inverse stricte (évite match "e" dans "Délivrance").
  - Calcul de la Bounding Box (AABB) à partir des 3 points.
- Fonction `analyser_hybride` refondue :
  - Génération de fichier crop temporaire.
  - Normalisation des coordonnées post-analyse.
  - Logs de débogage enrichis (comparaison dimensions Image vs Entité).

#### Frontend
- **Entity Creator** : Nouvelle interface pour saisir les 3 étiquettes de référence.
- **OCR Upload** : Visualisation corrigée (les zones bleues s'alignent maintenant parfaitement sur l'image originale après analyse).

### 📚 Documentation
- **OCR_ENGINE.md** : Documentation technique détaillée du pipeline hybride et du système AABB.

---

## [2.2.0] - 2026-01-27

### 🎉 Amélioration majeure de l'OCR Arabe

#### Prétraitement intelligent des images
- **Upscaling automatique** : Les petites zones (< 100px) sont automatiquement agrandies pour améliorer la reconnaissance
- **Isolation du texte foncé** : Nouvelle fonction `isolate_dark_text()` qui filtre les fonds texturés (passeports, documents officiels)
- **Multi-seuillage** : Test de 3 niveaux de seuillage (60, 80, 100) pour trouver l'optimal

#### Stratégie multi-variants
- **5 variants d'image testés** : isolation aggressive, moyenne, légère, grayscale, prétraitement CLAHE
- **4 modes PSM Tesseract** : 7 (ligne), 6 (bloc), 13 (brut), 8 (mot)
- **Sélection automatique** : Le meilleur résultat est conservé automatiquement

#### Résultats mesurés
- **Zone 'nom'** : 78% → **91%** (+13%)
- **Zone 'prenom'** : 42% → **82%** (+40%) 🚀

### 🔧 Modifications techniques

#### Backend (`ocr_engine.py`)
- Nouvelle fonction `upscale_for_ocr()` pour l'agrandissement d'images
- Nouvelle fonction `isolate_dark_text()` avec filtrage par composantes connectées
- Mode debug optionnel via `DEBUG_SAVE_IMAGES` flag
- Amélioration de la logique hybride Tesseract/EasyOCR

#### Performance
- L'analyse est légèrement plus lente (20 combinaisons testées) mais beaucoup plus précise
- Optimisation du choix du meilleur résultat entre moteurs

---

## [2.1.0] - 2026-01-03

### 🎉 Ajouts majeurs

#### Support QR Code et Codes-barres
- **Détection de QR codes** : Utilisation d'OpenCV pour détecter et décoder les QR codes
- **Types de zones** : Possibilité de définir des zones comme "Texte", "QR Code" ou "Code-barres"
- **Sélecteur de type** : Interface utilisateur avec dropdown pour choisir le type de zone
- **Confiance à 100%** : Les QR codes décodés ont une confiance maximale
- **Fallback automatique** : Si le QR code n'est pas détecté, l'OCR texte est utilisé

#### Nouvelle bibliothèque
- Ajout de **pyzbar** pour la détection de codes-barres (optionnel)
- Utilisation d'**OpenCV** comme moteur principal pour les QR codes
- Support de multiples formats : QR Code, EAN, Code128, Data Matrix, etc.

### 🔧 Modifications techniques

#### Backend
- **Nouveau module** : `app/utils/qrcode_utils.py`
  - Fonction `decoder_qrcode_opencv()` pour OpenCV
  - Fonction `decoder_qrcode()` pour pyzbar (optionnel)
  - Fonction `decoder_code_hybride()` avec fallback automatique
  - Gestion des erreurs de DLL manquante

- **Moteur OCR modifié** : `app/services/ocr_engine.py`
  - Détection automatique du type de zone
  - Traitement prioritaire des QR codes avant l'OCR
  - Support du champ `type` dans les zones

#### Frontend
- **Modèles TypeScript** (`models.ts`) :
  - Interface `Zone` avec champ `type?: 'text' | 'qrcode' | 'barcode'`
  - Support des résultats QR code

- **Composant Entités** (`entity-creator.component.*`) :
  - Ajout d'une colonne "Type" dans le tableau des zones
  - Sélecteur dropdown avec icônes (📝 Texte, 📦 QR Code, 🎫 Code-barres)
  - Méthode `changeZoneType()` pour modifier le type de zone
  - Transmission du type lors de la sauvegarde

- **Composant OCR** (`ocr-upload.component.ts`) :
  - Transmission du type de zone lors de l'analyse
  - Affichage du moteur utilisé dans les résultats

### 📚 Documentation
- **QRCODE_SUPPORT.md** : Guide complet du support QR Code et codes-barres
- **ZBAR_INSTALLATION.md** : Guide d'installation de zbar (optionnel)
- Documentation consolidée et simplifiée (10 fichiers supprimés)

### 🐛 Corrections
- Correction de la transmission du champ `type` lors de la sauvegarde d'entités
- Correction de la transmission du champ `type` lors de l'analyse OCR
- Gestion gracieuse de l'absence de DLL zbar (fallback sur OpenCV)

### ⚠️ Limitations connues
- Codes-barres nécessitent la DLL zbar (QR codes fonctionnent sans)
- Seul OpenCV est utilisé par défaut (pyzbar optionnel)

---

## [2.0.0] - 2025-12-03

### 🎉 Ajouts majeurs

#### Support PDF complet
- **Analyse OCR sur PDF** : Les utilisateurs peuvent maintenant uploader et analyser des fichiers PDF
- **Création d'entités avec PDF** : Possibilité d'utiliser un PDF comme image de référence pour créer des entités
- **Conversion automatique** : Les PDF sont automatiquement convertis en images JPEG haute qualité (300 DPI)
- **Première page uniquement** : Seule la première page du PDF est convertie pour l'instant

#### Nouvelle bibliothèque
- Ajout de **pypdfium2** pour la conversion PDF
  - Légère et performante
  - Pas de dépendances système complexes
  - Rendu haute qualité

### 🔧 Modifications techniques

#### Backend
- **Nouveau module** : `app/utils/pdf_utils.py`
  - Fonction `convert_pdf_to_image()` pour la conversion PDF → JPEG
  - Paramétrage de la résolution (DPI)
  - Gestion des erreurs de conversion

- **Routes modifiées** :
  - `app/api/file_routes.py` : Détection et conversion PDF dans `/api/upload`
  - `app/api/entity_routes.py` : Support PDF dans `/api/upload-image-entite`

- **Dépendances** :
  - Ajout de `pypdfium2` dans `requirements.txt`

#### Frontend
- **Composant OCR** (`ocr-upload.component.*`) :
  - Input file accepte `.pdf`
  - Détection du type de fichier
  - Gestion de la prévisualisation (désactivée pour PDF)
  - Label mis à jour : "Choisir une image ou un PDF"

- **Composant Entités** (`entity-creator.component.*`) :
  - Input file accepte `.pdf`
  - Label mis à jour : "Choisir une image ou un PDF"
  - Conversion transparente côté serveur

### 📚 Documentation
- **README.md** : Documentation complète du projet avec support PDF
- **PDF_SUPPORT.md** : Documentation technique détaillée du support PDF
- **GUIDE_PDF.md** : Guide utilisateur pour les fonctionnalités PDF
- **test_pdf_support.py** : Script de test pour la conversion PDF

### 🐛 Corrections
- Aucune correction dans cette version (nouvelle fonctionnalité)

### ⚠️ Limitations connues
- Seule la première page du PDF est convertie
- Format de sortie fixé à JPEG
- Résolution fixée à 300 DPI (modifiable dans le code)

---

## [1.0.0] - 2025-11-XX

### Fonctionnalités initiales

#### Analyse OCR
- Support des images (JPG, PNG, BMP, TIFF)
- Moteur Tesseract pour arabe et français
- Moteur EasyOCR en secours
- Analyse hybride automatique
- Niveau de confiance par zone

#### Gestion des entités
- Création de modèles d'extraction
- Définition de zones par dessin
- Drag & drop pour déplacer/redimensionner
- Coordonnées relatives
- Stockage JSON

#### Interface utilisateur
- Application Angular standalone
- Deux onglets : OCR Analysis et Entity Management
- Canvas interactif pour les zones
- Export JSON des résultats
- Statistiques par moteur OCR

#### Backend
- API Flask RESTful
- Upload de fichiers
- Gestion des sessions
- CORS configuré
- Stockage local des entités

---

## Versions futures prévues

### [2.2.0] - À venir
- [ ] Support complet de zbar pour tous les types de codes-barres
- [ ] Support multi-pages pour PDF
- [ ] Sélection de la page à convertir
- [ ] Paramétrage de la résolution dans l'interface
- [ ] Support PNG pour la conversion (en plus de JPEG)

### [2.3.0] - À venir
- [ ] Batch processing (traitement par lot)
- [ ] Interface de correction manuelle des résultats
- [ ] Historique des analyses
- [ ] Comparaison de résultats
- [ ] Export en CSV et Excel

### [3.0.0] - À venir
- [ ] API REST complète et documentée (Swagger)
- [ ] Authentification et gestion des utilisateurs
- [ ] Base de données (PostgreSQL/MongoDB)
- [ ] Déploiement Docker
- [ ] CI/CD
- [ ] Tests automatisés

---

## Format du changelog

Ce changelog suit le format [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

### Types de changements
- **Ajouts** : Nouvelles fonctionnalités
- **Modifications** : Changements dans les fonctionnalités existantes
- **Obsolète** : Fonctionnalités bientôt supprimées
- **Suppressions** : Fonctionnalités supprimées
- **Corrections** : Corrections de bugs
- **Sécurité** : Corrections de vulnérabilités
