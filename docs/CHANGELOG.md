# Changelog - EasyTess OCR

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [3.2.0] - 2026-04-25

### 🎉 Refactorisation complète du micro-service Extractor

#### Backend — Nettoyage architectural
- **Suppression de 6 routes OCR obsolètes** dans `file_routes.py` (155 → 21 lignes)
- **Refactorisation de `docx_routes.py`** en thin wrapper délégant à `document_routes.py`
- **Externalisation du mapping de labels** : `config_labels/default.json` remplace le dictionnaire hardcodé dans `pdf_extractor.py`
- **Endpoint `normalize-labels`** : nouveau paramètre `?mapping=<nom>` pour choisir un fichier de config alternatif
- **Limite de taille fichier** : `MAX_CONTENT_LENGTH = 50 Mo` dans `config.py` avec handler d'erreur 413 JSON structuré
- **Détection de sauts de page DOCX** : support de `w:br type="page"` et `w:lastRenderedPageBreak` pour la parité PDF/DOCX
- **Nettoyage de `requirements.txt`** : suppression des dépendances OCR-specific copiées par erreur

#### Backend — Documentation API (Swagger)
- **Intégration Flasgger** : Swagger UI accessible à `http://localhost:8083/apidocs/`
- **Documentation YAML** dans les docstrings des endpoints `extract-pdf`, `extract-document`, `normalize-labels`
- **Spec JSON** disponible à `/apispec.json`

#### Backend — Tests automatisés
- **29 tests pytest** dans `tests/test_extractor.py` couvrant 5 catégories :
  - Extraction DOCX (8 tests)
  - Normalisation des labels (7 tests)
  - Extraction de codes tarifaires (2 tests)
  - Configuration des labels (3 tests)
  - Endpoints API Flask (9 tests)

#### Frontend — Nettoyage massif
- **Suppression de 10 composants/services orphelins** hérités du module OCR (~150 kB de code mort)
- **Réduction de `models.ts`** : 13 → 8 interfaces (suppression des interfaces OCR inutilisées)
- **Extraction de helpers** dans le composant : `buildFormData()`, `downloadJsonFile()`, `buildHscodeData()`
- **Migration vers `firstValueFrom()`** pour les observables one-shot
- **Correction du port API** dans `document.service.ts` : 8082 → 8083

#### Frontend — Nouveau mode Hscode10All
- **Bouton `Hscode10All`** (📋) dans l'onglet Code
- **Pipeline identique à Hscode10** (extraction tarif → normalisation → téléchargement)
- **Exporte TOUS les champs normalisés** dans `hscode_all.json` (au lieu de seulement `{code, description}`)
- **Exclut les métadonnées internes** (`_page`, `_tableau`)

### 📚 Documentation
- **CLAUDE.md** : Arbre mis à jour, 6 modes Code, endpoints `extract-tariff-codes` et `normalize-labels`, conventions Swagger/tests/limite
- **CHANGELOG.md** : Entrée v3.2.0

---

## [3.1.0] - 2026-04-18

### 🎉 Outil d'optimisation des zones OCR

#### Nouvel outil CLI : `test_zone_optimizer.py`
- **Optimisation automatique** des coordonnées de zones d'entités pour maximiser la confiance OCR
- **Descente de gradient discrétisée** en 2 passes (grossière ±15% / fine ±3%)
- **Score composite** : `confiance_OCR × similarité_texte` pour une évaluation robuste
- **Application automatique** : mise à jour du JSON de l'entité avec backup horodaté
- **Interface CLI complète** avec `argparse` :
  - `-e / --entite` : nom de l'entité
  - `-z / --zone` : zone à optimiser (répétable)
  - `-t / --texte` : texte attendu (vérité terrain)
  - `-i / --image` : image de test personnalisée
  - `--dry-run` : aperçu sans modification
  - `--easyocr` : activer EasyOCR en plus de Tesseract

#### Rapports générés
- **Rapport HTML** visuel (glassmorphism, barres de progression, comparaison avant/après)
- **Rapport JSON** détaillé dans `tests_output/`

#### Résultats mesurés (entité `cni_algo_recto_001`)
- **Zone 'nom'** (حمرون) : score 12% → **87.8%** (+75.7%) 🚀
- **Zone 'prenom'** (محمد) : score 94% → **96%** (+2%)

### 📚 Documentation
- **README.md** : Nouvelle section "Optimisation des zones OCR" avec syntaxe et exemples CLI
- **INDEX.md** : Ajout de l'entrée dans la navigation et le tableau résumé
- **QUICKSTART.md** : Ajout du conseil d'optimisation des zones
- **OCR_ENGINE.md** : Nouvelle section sur l'outil d'optimisation
- **CHANGELOG.md** : Entrée v3.1.0

---

## [3.0.0] - 2026-04-08

### 🎉 Scission en Micro-services

#### Architecture totalement refondée
- **Séparation des backends** : L'ancien monolithe `easytess-backend` a été découpé en :
  - `backend/app_ocr` (port 8082) — API dédiée OCR, entités, ancres, QR codes
  - `backend/app_extractor` (port 8083) — API dédiée extraction PDF/DOCX, conversion Word
  - `backend/core_lib` — Bibliothèque partagée installable (`pip install -e .`)
- **Séparation des frontends** : L'ancien monolithe `easytess-frontend` a été découpé en :
  - `frontend_ocr` (port 4100) — Interface Angular 18+ dédiée OCR (Analyse + Gestion Entités)
  - `frontend_extractor` — Interface Angular 18+ dédiée Extraction (PDF/DOCX + Conversion)
- **Indépendance totale** : Chaque service peut être lancé, déployé et maintenu séparément
- **Suppression des anciens dossiers** : `easytess-backend/` et `easytess-frontend/` ont été retirés

#### Avantages
- Déploiement ciblé : seul le service nécessaire est lancé (moins de mémoire, plus rapide)
- Scalabilité : chaque service peut évoluer indépendamment
- Maintenabilité : code plus lisible et séparation claire des responsabilités
- Extensibilité : ajout facile d'un nouveau micro-service (ex: `app_invoice`)

### 🔧 Modifications techniques
- Migration des entités JSON vers `backend/app_ocr/entities/`
- Migration des uploads vers `backend/app_ocr/uploads/`
- Mise à jour des chemins absolus dans les fichiers JSON d'entités
- Nettoyage des composants frontend (suppression des imports croisés)
- Mise à jour complète de la documentation (README, QUICKSTART, CLAUDE.md, CHANGELOG, INDEX, guides)

---

## [2.6.0] - 2026-03-10

### 🎉 Refonte du système de repérage des zones OCR

#### Détection du cadre basée sur les ancres réelles
- **Priorité à la DÉTECTION** : `get_anchor_edge()` utilise désormais la position détectée des ancres dans l'image courante (et non plus `position_base` qui ne convient qu'à l'image de référence)
- **Translation rigide** : la position du cadre vient de la détection, mais les dimensions sont FORCÉES depuis `dimensions_absolues` du cadre de référence → préserve la qualité OCR
- **Fallback intelligent** : si la détection échoue pour une ancre, `position_base` est utilisé en repli

#### Coordonnées relatives au cadre (et non à l'image)
- Les coordonnées retournées par `analyser_hybride()` sont désormais relatives au cadre détecté (0-1), pas à l'image entière
- Nouvel élément `cadre_detecte` retourné par l'API : `{x, y, width, height}` en relatif (0-1) par rapport à l'image originale
- Le frontend reconvertit les coords cadre-relatives en image-relatives uniquement pour l'affichage

#### Visualisation du cadre détecté
- **Rectangle vert en pointillés** tracé autour du cadre de l'entité sur le canvas après analyse
- **Label avec dimensions** en pixels (ex: `CADRE (896×486px)`)
- Les zones OCR continuent d'être affichées en bleu plein à l'intérieur du cadre vert

### 🐛 Corrections critiques

- **Fix crop RGBA** : les images PNG avec canal alpha (RGBA) sont désormais converties en RGB avant sauvegarde en JPEG. Sans ce fix, le crop échouait silencieusement et Tesseract analysait l'image originale entière → résultats OCR complètement faux
- **Fix normalisation des coordonnées** : suppression de la double normalisation qui pouvait fausser les coords retournées

### 🔧 Modifications techniques

#### Backend (`ocr_engine.py`)
- `get_anchor_edge()` : inversion des priorités (détection > position_base)
- `analyser_hybride()` : retourne maintenant un tuple `(resultats, alertes, cadre_detecte)` au lieu de `(resultats, alertes)`
- Suppression de la logique de re-mapping des coordonnées vers l'image originale
- Ajout de la conversion RGBA → RGB dans le bloc de rognage physique

#### Backend (`ocr_routes.py`)
- `_analyser_un_fichier()` et `api_analyser()` : gestion du 3ème retour `cadre_detecte`
- `cadre_detecte` inclus dans les réponses JSON

#### Frontend (`ocr-upload.component.ts`)
- `drawCanvas()` : tracé du cadre vert (pointillés) + reconversion cadre-relative → image-relative pour les zones bleues
- Utilisation de `cadre_detecte` pour le positionnement correct des rectangles

#### Frontend (`models.ts`)
- Interface `AnalyseResponse` : ajout du champ optionnel `cadre_detecte`

### ⚠️ Principes établis
- **Repérage ↔ OCR** : ne jamais modifier l'un sans vérifier l'autre. Ces deux aspects sont étroitement couplés.
- **Tester sur plusieurs images** : valider avec l'image de référence ET des images différentes (dimensions, formats PNG/JPEG)

---

## [2.5.0] - 2026-02-25

### 🎉 Ajouts majeurs

#### Extraction de contenu documentaire (PDF + Word)
- **Extraction PDF** : Extraction texte + tableaux depuis un PDF via `pdfplumber`
- **Extraction DOCX** : Extraction texte + tableaux (vrais tableaux Word + pseudo-tableaux tabulés)
- **Extraction unifiée** : Un seul endpoint acceptant PDF et DOCX, auto-détection du format
- **Conversion PDF → Word** : Reconstruction du contenu PDF en document `.docx` fidèle (texte, tableaux, en-têtes, sauts de page)
- **Export JSON** : Export client-side du contenu structuré extrait

#### Détection avancée des tableaux
- **4 stratégies de détection** :
  - `standard` : Lignes visibles (bordures)
  - `text` : Alignement texte (tableaux sans bordures)
  - `lines_strict` : Lignes nettes uniquement
  - `auto` : `standard` en premier, fallback `text` si aucun résultat
- **Détection d'en-têtes** : Heuristique pour identifier les lignes d'en-tête
- **Métadonnées enrichies** : Dimensions, bounding box, en-têtes, statistiques par page

#### Frontend — Nouvelle section "Extraction de Documents"
- **2 sections dans la navigation principale** : "EasyTess — OCR" et "Extraction de Documents"
- **3 modes d'extraction** : Extraction Unifiée, Extraction PDF, Conversion PDF→Word
- **Drag & drop** avec validation de format et prévisualisation
- **Panneau d'options** : Stratégie, filtre de pages, filtre de colonnes
- **Tableaux expandables** avec en-têtes détectés et numérotation
- **Aperçu JSON intégré** (toggle)
- **Conversion PDF→DOCX** avec téléchargement direct du fichier Word
- **Export JSON** : Téléchargement client-side du contenu extrait

### 🔧 Modifications techniques

#### Backend — Nouveaux services
- **`app/services/pdf_extractor.py`** : Refondu — multi-stratégie, métadonnées, retourne `(content, stats)`
- **`app/services/docx_extractor.py`** : Extraction Word (vrais tableaux + pseudo-tableaux tabulés)
- **`app/services/pdf_to_docx.py`** : Nouveau — conversion contenu structuré → .docx avec styles

#### Backend — Nouvelles routes
- **`app/api/document_routes.py`** : 3 endpoints :
  - `POST /api/extract-pdf` : Extraction PDF uniquement
  - `POST /api/extract-document` : Extraction unifiée PDF ou DOCX
  - `POST /api/convert-pdf-to-docx` : Conversion PDF → Word avec download
- **`app/__init__.py`** : Enregistrement du blueprint `document_bp`

#### Backend — Dépendances
- Ajout de `pdfplumber` dans `requirements.txt`

#### Frontend — Nouveaux fichiers
- **`services/document.service.ts`** : Service Angular pour les appels API extraction + conversion
- **`services/models.ts`** : Interfaces `DocumentBloc`, `ExtractDocumentResponse`, `ConvertPdfResponse`, etc.
- **`components/document-extractor.component.*`** : Composant complet (TS + HTML + CSS)

#### Frontend — Fichiers modifiés
- **`app.component.ts`** : 2 sections (`ocr` | `extraction`) + sous-onglets OCR (`analyse` | `entity`)
- **`app.component.html`** : Navigation principale + sous-navigation
- **`app.component.css`** : Layout section-nav + sub-tabs

### 📚 Documentation
- **CLAUDE.md** : Refondu — architecture complète, 2 sections, paramètres API
- **CHANGELOG.md** : Entrée v2.5.0
- **README.md** : Mise à jour fonctionnalités et architecture

### 🧪 Tests
- **`test_document_extraction.py`** : Script de test complet (extraction PDF/DOCX, conversion, comparaison stratégies)

---

## [2.4.0] - 2026-02-23

### 🎉 Ajouts majeurs

#### Analyse OCR par Lot (Batch Processing)
- **3 modes d'analyse** : Fichier unique, Multi-fichiers, Dossier
- **Batch synchrone** : `POST /api/analyser-batch` pour les petits lots
- **Batch asynchrone** : `POST /api/analyser-batch-async` avec traitement en arrière-plan
- **Progression SSE** : `GET /api/batch-progress/<job_id>` pour le suivi temps réel
- **Polling fallback** : `GET /api/batch-result/<job_id>` si SSE indisponible
- **Analyse dossier serveur** : `POST /api/analyser-dossier` pour analyser un dossier côté serveur
- **Upload batch** : `POST /api/upload-batch` pour uploader N fichiers à la fois
- **Export batch** : `POST /api/export-json-batch` pour exporter tous les résultats en JSON

#### Frontend
- **Toggle 3 modes** : Interface avec 3 boutons (📄 Fichier unique / 📑 Multi-fichiers / 📁 Dossier)
- **Sélection dossier** : `webkitdirectory` pour sélectionner un dossier entier
- **Barre de progression** : Temps réel avec pourcentage et nom du fichier en cours
- **Résultats dépliables** : Clic sur chaque fichier pour voir les détails par zone
- **Export global** : Bouton pour télécharger un JSON consolidé de tous les résultats

### 🔧 Modifications techniques

#### Backend (`ocr_routes.py`)
- Fonction `_analyser_un_fichier()` extraite pour réutilisation
- Thread unique avec `app.app_context()` (pas de ThreadPoolExecutor — les sous-threads perdent le contexte Flask)
- Gestion thread-safe avec `threading.Lock`
- Nettoyage automatique des jobs terminés après livraison SSE

#### Backend (`file_routes.py`)
- Endpoint `POST /api/upload-batch` : upload multi-fichiers avec conversion PDF
- Endpoint `POST /api/export-json-batch` : export JSON consolidé

#### Frontend
- `models.ts` : Interfaces `BatchUploadResponse`, `BatchFileResult`, `BatchAnalyseResponse`
- `file.service.ts` : `uploadMultipleImages()`, `downloadBatchJsonFile()`
- `ocr.service.ts` : `analyserBatch()`, `analyserBatchAsync()`, `connectBatchProgress()`, `getBatchResult()`
- `ocr-upload.component.ts` : 3 modes, SSE + polling fallback, NgZone, OnDestroy
- `ocr-upload.component.html` : Toggle, folder input, barre de progression
- `ocr-upload.component.css` : Styles toggle, file chips, batch cards, progress bar

### 📚 Documentation
- **CLAUDE.md** : Guide de développement pour agents IA (architecture, gotchas, endpoints)
- **CHANGELOG.md** : Mise à jour avec v2.4.0
- **README.md** : Ajout de la fonctionnalité batch dans les features

### 🐛 Corrections
- Fix `Working outside of application context` : Les threads utilisent `app.app_context()` et un traitement séquentiel (pas de ThreadPoolExecutor)

---

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

### [3.2.0] - ✅ Fait
- [x] API REST documentée (Swagger / Flasgger)
- [x] Tests automatisés (29 tests pytest)

### [4.0.0] - À venir
- [ ] Support complet de zbar pour tous les types de codes-barres
- [ ] Support multi-pages pour PDF (OCR)
- [ ] Paramétrage de la résolution dans l'interface
- [ ] Interface de correction manuelle des résultats
- [ ] Authentification et gestion des utilisateurs
- [ ] Base de données (PostgreSQL/MongoDB)
- [ ] Déploiement Docker (un container par micro-service)
- [ ] CI/CD

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
