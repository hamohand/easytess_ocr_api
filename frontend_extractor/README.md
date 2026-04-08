# EasyTess Extraction — Frontend

Application Angular 18+ dédiée à l'extraction de contenu structuré (PDF/DOCX) et à la conversion PDF → Word.

## Démarrage

```bash
npm install
ng serve
```

Le serveur de développement démarre sur le port configuré dans `angular.json`. L'application se recharge automatiquement lors de modifications.

## Backend associé

Ce frontend communique avec `backend/app_extractor` (port 8083). Assurez-vous qu'il est lancé avant d'utiliser l'application.

```bash
cd ../backend/app_extractor
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
