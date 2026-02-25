# CLAUDE.md — Guide de développement pour agents IA

Ce fichier décrit le projet EasyTess OCR pour les agents IA qui contribuent au code.

## Vue d'ensemble

**EasyTess** est une application d'analyse OCR avec gestion d'entités, composée d'un backend Flask (Python) et d'un frontend Angular (TypeScript).

## Architecture

```
easytess_api/
├── easytess-backend/           # API Flask (port 8082)
│   ├── run.py                  # Point d'entrée
│   ├── config.py               # Configuration
│   ├── app/
│   │   ├── __init__.py         # create_app(), CORS, blueprints
│   │   ├── api/
│   │   │   ├── file_routes.py  # Upload, upload-batch, export JSON
│   │   │   ├── ocr_routes.py   # Analyse simple, batch sync, batch async (SSE), dossier
│   │   │   └── entity_routes.py# CRUD entités
│   │   ├── services/
│   │   │   ├── ocr_engine.py   # Moteurs OCR (Tesseract + EasyOCR), analyse hybride, AABB
│   │   │   ├── entity_manager.py
│   │   │   ├── pdf_extractor.py    # Extraction contenu PDF (texte + tableaux) — pdfplumber
│   │   │   ├── docx_extractor.py   # Extraction contenu Word (texte + tableaux) — python-docx
│   │   │   └── pdf_to_docx.py      # Conversion PDF → Word (.docx)
│   │   └── utils/
│   │       ├── pdf_utils.py    # Conversion PDF → image (pour OCR)
│   │       ├── image_utils.py  # Traitement images
│   │       └── qrcode_utils.py # Détection QR codes
│   ├── entities/               # Stockage entités (JSON)
│   └── uploads/                # Fichiers uploadés
│
├── easytess-frontend/          # Angular 17+ (port 4200)
│   └── src/app/
│       ├── components/
│       │   ├── ocr-upload.component.*      # Analyse OCR (3 modes: single/multi/folder)
│       │   └── entity-creator.component.*  # Création entités
│       └── services/
│           ├── file.service.ts    # Upload simple/batch, export JSON
│           ├── ocr.service.ts     # Analyse simple/batch/async, SSE progress
│           ├── entity.service.ts  # CRUD entités
│           └── models.ts          # Interfaces TypeScript
│
└── docs/                       # Documentation
```

## Commandes essentielles

```bash
# Backend
cd easytess-backend
pip install -r requirements.txt
python run.py                    # → http://localhost:8082

# Frontend
cd easytess-frontend
npm install
ng serve                         # → http://localhost:4200

# Build frontend (dev)
npx ng build --configuration=development
```

## Points d'attention

### Backend — Flask Context
- `ocr_engine.py` utilise `flask.current_app.config` dans `detecter_ancres()` (ligne ~440)
- **Les threads en arrière-plan** doivent envelopper leur code dans `with app.app_context():`
- **Ne PAS utiliser `ThreadPoolExecutor`** car les sous-threads perdent le contexte Flask
- Utiliser un seul thread + traitement séquentiel dans `app.app_context()`

### Backend — Coordonnées
- Les coordonnées des zones sont **relatives** (0.0 à 1.0), pas en pixels
- Le système AABB utilise 3 ancres (Haut, Droite, Gauche) pour aligner les zones
- `analyser_hybride()` rogne physiquement l'image selon le cadre détecté

### Frontend — Signaux Angular
- Le composant utilise des **signals Angular** (pas de BehaviorSubject)
- 3 modes : `single`, `multi`, `folder` (toggle via `activeMode` signal)
- SSE via `EventSource` natif avec `NgZone.run()` pour la détection de changements
- Cleanup du `EventSource` dans `ngOnDestroy()`

### Langues OCR
- Par défaut : Arabe + Français (`ara+fra` pour Tesseract, `['ar', 'en']` pour EasyOCR)
- Configurable par zone via le champ `lang`

## Endpoints API principaux

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
| POST | `/api/extract-pdf` | Extraction contenu PDF (texte + tableaux) |
| POST | `/api/extract-docx` | Extraction contenu Word |
| POST | `/api/extract-document` | Extraction unifiée (PDF ou DOCX, auto-détection) |
| POST | `/api/convert-pdf-to-docx` | Conversion PDF → Word (.docx) |

## Conventions

- **CSS Budget** : `entity-creator.component.css` dépasse le budget production (~12 kB). Le build `--configuration=development` fonctionne toujours.
- **Pas de tests automatisés** : Tester manuellement via le navigateur.
- **Stockage** : Entités en JSON dans `entities/`, uploads dans `uploads/`.
- **Pas d'auth** : L'API est ouverte (usage interne).
