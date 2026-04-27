# CLAUDE.md — Guide de développement pour agents IA

Ce fichier décrit le projet EasyTess pour les agents IA qui contribuent au code.

## Vue d'ensemble

**EasyTess** est une plateforme d'analyse OCR et d'extraction de documents, organisée en **micro-services indépendants**. Deux applications distinctes :
1. **EasyTess-OCR** (`app_ocr` + `frontend_ocr`) : Analyse OCR avec gestion d'entités (zones, ancres, QR codes)
2. **Extraction de Documents** (`app_extractor` + `frontend_extractor`) : Extraction de contenu structuré (texte + tableaux) depuis PDF/DOCX, conversion PDF → Word

## Architecture

```
easytess_ocr_api/
├── backend/
│   ├── core_lib/                  # Bibliothèque partagée (installable via pip install -e .)
│   │   └── easy_core/
│   │       ├── pdf_utils.py       # Conversion PDF → image (pour OCR)
│   │       ├── image_utils.py     # Traitement images, patch Pillow
│   │       └── qrcode_utils.py    # Détection QR codes / codes-barres
│   │
│   ├── app_ocr/                   # API Flask OCR (port 8082)
│   │   ├── run.py                 # Point d'entrée
│   │   ├── config.py              # Configuration
│   │   ├── entities/              # Stockage entités (JSON)
│   │   ├── uploads/               # Fichiers uploadés
│   │   └── app/
│   │       ├── __init__.py        # create_app(), CORS, blueprints
│   │       ├── api/
│   │       │   ├── file_routes.py     # Upload, upload-batch, export JSON
│   │       │   ├── ocr_routes.py      # Analyse simple, batch sync, batch async (SSE), dossier
│   │       │   └── entity_routes.py   # CRUD entités
│   │       ├── services/
│   │       │   ├── ocr_engine.py      # Moteurs OCR (Tesseract + EasyOCR), analyse hybride, AABB
│   │       │   ├── entity_manager.py  # CRUD fichiers JSON entités
│   │       │   └── image_matcher.py   # Template matching ORB
│   │       └── utils/                 # Utilitaires spécifiques OCR
│   │
│   └── app_extractor/             # API Flask Extraction (port 8083)
│       ├── run.py                 # Point d'entrée
│       ├── config.py              # Configuration (MAX_CONTENT_LENGTH=50Mo)
│       ├── config_labels/         # Mappings de normalisation des étiquettes
│       │   └── default.json       # Mapping par défaut (col_XX → noms lisibles)
│       ├── tests/
│       │   └── test_extractor.py  # 29 tests (pytest)
│       └── app/
│           ├── __init__.py        # create_app(), CORS, Swagger (Flasgger), error handlers
│           ├── api/
│           │   ├── document_routes.py  # Extraction unifiée PDF/DOCX + conversion + normalisation
│           │   ├── docx_routes.py      # Extraction DOCX (thin wrapper → document_routes)
│           │   └── file_routes.py      # Serving fichiers uploadés uniquement
│           └── services/
│               ├── pdf_extractor.py    # Extraction contenu PDF — pdfplumber + normalisation
│               ├── docx_extractor.py   # Extraction contenu Word — python-docx (avec pages)
│               └── pdf_to_docx.py      # Conversion PDF → Word (.docx)
│
├── frontend_ocr/                  # Angular 18+ dédié OCR (port 4100)
│   └── src/app/
│       ├── app.component.*               # Layout principal OCR (2 sous-onglets)
│       ├── components/
│       │   ├── ocr-upload.component.*         # Analyse OCR (3 modes: single/multi/folder)
│       │   └── entity-creator.component.*     # Création/gestion des entités
│       └── services/
│           ├── file.service.ts       # Upload simple/batch, export JSON
│           ├── ocr.service.ts        # Analyse simple/batch/async, SSE progress
│           ├── entity.service.ts     # CRUD entités
│           └── models.ts             # Interfaces TypeScript OCR
│
├── frontend_extractor/            # Angular 18+ dédié Extraction (port 4200 ou conf)
│   └── src/app/
│       ├── app.component.*               # Layout principal Extraction
│       ├── components/
│       │   └── document-extractor.component.*  # Extraction PDF/DOCX + conversion + pipeline tarif
│       └── services/
│           ├── document.service.ts   # Extraction + conversion + normalisation + tariff codes
│           ├── models.ts             # Interfaces TypeScript Extraction (8 interfaces)
│           └── index.ts              # Barrel exports
│
└── docs/                          # Documentation
```

## Commandes essentielles

```bash
# Installer le noyau commun (une seule fois)
cd backend/core_lib
pip install -e .

# Backend OCR
cd backend/app_ocr
pip install -r requirements.txt
python run.py                    # → http://localhost:8082

# Backend Extraction (dans un autre terminal)
cd backend/app_extractor
pip install -r requirements.txt
python run.py                    # → http://localhost:8083
                                 # Swagger UI → http://localhost:8083/apidocs/

# Tests Extractor
cd backend/app_extractor
python -m pytest tests/ -v       # 29 tests

# Frontend OCR
cd frontend_ocr
npm install
ng serve                         # → http://localhost:4100

# Frontend Extraction (dans un autre terminal)
cd frontend_extractor
npm install
ng serve                         # → port configuré dans angular.json

# Build frontend (dev)
npx ng build --configuration=development
```

## Points d'attention

### Architecture — Séparation des services
- Les backends `app_ocr` et `app_extractor` sont **totalement indépendants** et tournent sur des ports différents
- Ils partagent **uniquement** `core_lib` (utilitaires communs) via `pip install -e .`
- Les frontends `frontend_ocr` et `frontend_extractor` sont aussi **indépendants** 
- Chaque frontend pointe vers **son propre backend** (OCR → 8082, Extraction → 8083)
- Pour ajouter un nouveau micro-service : créer `backend/app_xxx` + `frontend_xxx` sur de nouveaux ports

### Backend — Flask Context
- `ocr_engine.py` utilise `flask.current_app.config` dans `detecter_ancres()` (ligne ~440)
- **Les threads en arrière-plan** doivent envelopper leur code dans `with app.app_context():`
- **Ne PAS utiliser `ThreadPoolExecutor`** car les sous-threads perdent le contexte Flask
- Utiliser un seul thread + traitement séquentiel dans `app.app_context()`

### Backend — Coordonnées et Cadre de Référence (OCR)
- Les coordonnées des zones sont **relatives au cadre** (0.0 à 1.0), pas en pixels et pas relatives à l'image
- Le système AABB utilise 4 ancres (Haut, Droite, Gauche, Bas) pour aligner les zones
- **Algorithme de détection du cadre** :
  1. Détection des ancres dans l'image courante (PRIORITÉ à la détection réelle > position_base)
     - **3 méthodes par ancre**, en priorité :
       1. **Mot-Clé / Regex OCR** : Texte trouvé sur le document
       2. **Template Image** : Pattern Matching OpenCV (ORB)
       3. **Formule Algorithmique** : Déduite des autres ancres via `ast.parse` (ex: `H + 0.40 * RH`)
     - Variables formules : `H` (haut.y), `B` (bas.y), `G` (gauche.x), `D` (droite.x)
     - Variables d'échelle : `RH` (ref_height/img_height), `RW` (ref_width/img_width)
     - Utiliser `RH`/`RW` pour des formules invariantes à la taille d'image
     - Résolution multi-passes pour dépendances croisées
  2. Le sommet haut-gauche du cadre devient l'origine (0,0) du repère
  3. **Translation rigide** : les dimensions du cadre sont FORCÉES depuis `dimensions_absolues` (référence), seule la position vient de la détection
  4. Les zones restent identiques à celles de l'image de référence (pas de mise à l'échelle)
- `analyser_hybride()` rogne physiquement l'image selon le cadre détecté et retourne un 3ème élément `cadre_detecte`
- **`cadre_detecte`** : `{x, y, width, height}` en relatif (0-1) par rapport à l'image originale, utilisé par le frontend pour dessiner le cadre vert
- **Crop RGBA** : les images PNG avec canal alpha sont converties en RGB avant sauvegarde JPEG du crop

### Backend — Extraction de documents (app_extractor)
- `pdf_extractor.py` retourne un tuple `(content, stats)` — l'ancien code ne retournait que `content`
- **4 stratégies de détection des tableaux** : `auto`, `standard`, `text`, `lines_strict`
- `auto` essaie `standard` puis fallback `text` si aucun tableau détecté
- Les métadonnées de tableaux incluent en-têtes, bbox, dimensions
- `pdf_to_docx.py` reconstruit un .docx à partir du contenu structuré
- **`normalize_labels()`** : renomme les clés des lignes extraites selon un mapping chargé depuis `config_labels/<mapping_name>.json`. Le fichier par défaut est `config_labels/default.json`. La correspondance est **exacte** (pas partielle) — ajouter la variante exacte au fichier de config si une nouvelle forme apparaît. Le paramètre `mapping_name` permet de choisir un mapping différent (ex: `chapitre_84`). Fallback vers des valeurs hardcodées si le fichier est absent.

### Frontend OCR — 2 sous-onglets
- **Sous-onglet "Analyse OCR"** : analyse OCR (3 modes: single/multi/folder)
- **Sous-onglet "Gestion des Entités"** : création/édition des entités
- **Visualisation post-analyse** : cadre de l'entité tracé en **vert pointillé** + zones OCR en **bleu plein** sur le canvas

### Frontend Extraction — Interface dédiée
- **Extraction** : 3 modes (`unified`, `pdf`, `convert`)
- **Code** : 6 modes (`position` → `etiquettes` → `hscode` → `hscode10` → `hscode10all` → `hscode10folder`)
- Le composant `document-extractor` utilise des **signals Angular** et `FormsModule` pour les options
- **Swagger UI** disponible à `http://localhost:8083/apidocs/`
- **Limite upload** : 50 Mo max (`MAX_CONTENT_LENGTH`), handler 413 JSON

### Frontend — Flux onglet Code (Tarif douanier)
Les 3 modes de l'onglet **Code** sont conçus pour s'enchaîner sur le même PDF :
1. **Position** — extrait les lignes des tableaux contenant une colonne `"col_04"` ou `"Désignation des Produits"`, en écartant celles qui ont plusieurs codes tarifaires (`XXXX.XX.XX.XX`) (`/api/extract-tariff-codes`)
2. **Étiquettes** — normalise les noms de colonnes (`/api/normalize-labels`) → produit `etiquettes.json`
3. **Hscode** — génère `hscode.json` côté client (pas d'appel API) à partir des données d'Étiquettes :
   - `code` ← clé contenant `"position"` (recherche partielle insensible à la casse), **chiffres uniquement** (`replace(/[^0-9]/g, '')`)
   - `description` ← clé contenant `"désignation"` ou `"designation"`
- **Hscode10** — pipeline tout-en-un : extraction des codes tarifaires + normalisation + génération `hscode.json` (même résultat que les 3 étapes manuelles)
- **Hscode10All** — identique à Hscode10 mais exporte **tous les champs normalisés** (`hscode_all.json`) au lieu de seulement `{code, description}`
- **Hscode10-Dossier** — même pipeline Hscode10 mais appliqué à un dossier entier de PDFs
- Les résultats sont **partagés** entre les modes (pas de reset lors du switch entre eux)
- Le mode `hscode` n'a pas de dropzone ni de panneau options (traitement purement client)

### Frontend — Signaux Angular
- Tous les composants utilisent des **signals Angular** (pas de BehaviorSubject)
- OCR : 3 modes : `single`, `multi`, `folder` (toggle via `activeMode` signal)
- Extraction (onglet **Extraction**) : 3 modes : `unified`, `pdf`, `convert`
- Extraction (onglet **Code**) : 6 modes : `position`, `etiquettes`, `hscode`, `hscode10`, `hscode10all`, `hscode10folder`
- SSE via `EventSource` natif avec `NgZone.run()` pour la détection de changements
- Cleanup du `EventSource` dans `ngOnDestroy()`

### Langues OCR
- Par défaut : Arabe + Français (`ara+fra` pour Tesseract, `['ar', 'en']` pour EasyOCR)
- Configurable par zone via le champ `lang`

## Endpoints API principaux

### OCR & Fichiers (app_ocr — port 8082)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/upload` | Upload fichier unique |
| POST | `/api/upload-batch` | Upload multi-fichiers |
| POST | `/api/analyser` | Analyse OCR fichier unique |
| POST | `/api/analyser-batch` | Analyse batch synchrone |
| POST | `/api/analyser-batch-async` | Analyse batch async → retourne `job_id` |
| GET | `/api/batch-progress/<job_id>` | SSE progression temps réel |
| GET | `/api/batch-result/<job_id>` | Polling fallback progression |
| POST | `/api/analyser-dossier` | Analyse dossier côté serveur |
| POST | `/api/export-json-file` | Export JSON résultats |
| POST | `/api/export-json-batch` | Export JSON batch |
| GET/POST | `/api/entites` | Lister / créer entités |
| GET/PUT/DELETE | `/api/entites/<nom>` | CRUD entité |

### Extraction & Conversion de documents (app_extractor — port 8083)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/extract-pdf` | Extraction contenu PDF (texte + tableaux) |
| POST | `/api/extract-docx` | Extraction contenu Word (.docx) |
| POST | `/api/extract-document` | Extraction unifiée (PDF ou DOCX, auto-détection) |
| POST | `/api/convert-pdf-to-docx` | Conversion PDF → Word (.docx) avec téléchargement |
| POST | `/api/extract-tariff-codes` | Extraction des lignes avec un code tarifaire unique |
| POST | `/api/normalize-labels` | Normalisation des étiquettes (mapping configurable) |

#### Paramètres communs (`extract-*` et `convert-*`)
- `file` : fichier PDF ou DOCX (obligatoire)
- `table_columns` : JSON array d'indices de colonnes (optionnel, ex: `[0, 2]`)
- `pages` : JSON array de pages 1-based (optionnel, PDF uniquement, ex: `[1, 3]`)
- `strategy` : Stratégie de détection tableaux (optionnel, PDF uniquement) — `auto` | `standard` | `text` | `lines_strict`
- `download` : `true`/`false` (pour `convert-pdf-to-docx` uniquement)

## Conventions

- **CSS Budget** : `entity-creator.component.css` dépasse le budget production (~12 kB). Le build `--configuration=development` fonctionne toujours.
- **Tests automatisés** : `python -m pytest tests/ -v` depuis `backend/app_extractor/` (29 tests).
- **Swagger UI** : Disponible à `http://localhost:8083/apidocs/` (Flasgger). Spec JSON à `/apispec.json`.
- **Stockage** : Entités en JSON dans `entities/`, uploads dans `uploads/`.
- **Pas d'auth** : L'API est ouverte (usage interne).
- **Limite upload** : 50 Mo par fichier (`MAX_CONTENT_LENGTH` dans `config.py`).

## ⚠️ Principe fondamental : Repérage ↔ OCR

**Ne jamais modifier le repérage des zones sans vérifier la qualité OCR, et inversement.**
Ces deux aspects sont étroitement couplés :
- Modifier le calcul du cadre peut décaler les zones → dégradation OCR
- Modifier le prétraitement OCR peut compenser/masquer un mauvais repérage
- Toujours tester les deux ensemble avant de valider un changement
