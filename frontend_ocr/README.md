# EasyTess OCR — Frontend

Application Angular 18+ dédiée à l'analyse OCR et à la gestion des entités.

## Démarrage

```bash
npm install
ng serve
```

Le serveur de développement démarre sur `http://localhost:4100/`. L'application se recharge automatiquement lors de modifications.

## Backend associé

Ce frontend communique avec `backend/app_ocr` (port 8082). Assurez-vous qu'il est lancé avant d'utiliser l'application.

```bash
cd ../backend/app_ocr
python run.py
```

## Build

```bash
ng build
```

Les artefacts sont générés dans `dist/`.

## Ressources

- [Angular CLI Overview](https://angular.dev/tools/cli)
- [Documentation projet](../docs/QUICKSTART.md)
