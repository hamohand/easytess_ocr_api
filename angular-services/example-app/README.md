# 🚀 Exemple d'Application Angular EasyTess

Application Angular 18+ standalone complète pour utiliser l'API EasyTess OCR.

## 📁 Structure

```
example-app/
├── main.ts              # Point d'entrée
├── app.config.ts        # Configuration de l'app
├── app.component.ts     # Composant principal
├── app.component.html   # Template principal
├── app.component.css    # Styles du composant principal
├── index.html           # HTML de base
└── styles.css           # Styles globaux
```

## 🎯 Fonctionnalités

- ✅ Navigation par onglets (Analyse OCR / Créer entité)
- ✅ Design moderne avec gradients
- ✅ Responsive (mobile, tablette, desktop)
- ✅ Loading spinner
- ✅ Standalone components (Angular 18+)
- ✅ Signals pour la réactivité

## 📦 Installation

### 1. Créer un nouveau projet Angular

```bash
# Si vous n'avez pas Angular CLI
npm install -g @angular/cli

# Créer un nouveau projet
ng new easytess-frontend --standalone --routing=false --style=css
cd easytess-frontend
```

### 2. Copier les fichiers

Copiez les fichiers de cet exemple dans votre projet :

```
easytess-frontend/
├── src/
│   ├── main.ts                    # ← Remplacer
│   ├── index.html                 # ← Remplacer
│   ├── styles.css                 # ← Remplacer
│   └── app/
│       ├── app.config.ts          # ← Remplacer
│       ├── app.component.ts       # ← Remplacer
│       ├── app.component.html     # ← Remplacer
│       ├── app.component.css      # ← Remplacer
│       ├── services/              # ← Copier tout le dossier
│       │   ├── models.ts
│       │   ├── ocr.service.ts
│       │   ├── entity.service.ts
│       │   ├── file.service.ts
│       │   └── index.ts
│       └── components/            # ← Copier tout le dossier
│           ├── ocr-upload.component.ts
│           ├── ocr-upload.component.html
│           ├── ocr-upload.component.css
│           ├── entity-creator.component.ts
│           ├── entity-creator.component.html
│           └── entity-creator.component.css
```

### 3. Vérifier les dépendances

Assurez-vous que `package.json` contient :

```json
{
  "dependencies": {
    "@angular/animations": "^18.0.0",
    "@angular/common": "^18.0.0",
    "@angular/compiler": "^18.0.0",
    "@angular/core": "^18.0.0",
    "@angular/forms": "^18.0.0",
    "@angular/platform-browser": "^18.0.0",
    "@angular/platform-browser-dynamic": "^18.0.0",
    "rxjs": "~7.8.0",
    "tslib": "^2.3.0",
    "zone.js": "~0.14.0"
  }
}
```

Puis :
```bash
npm install
```

## 🚀 Lancement

### 1. Démarrer le backend Flask

```bash
cd easytess-backend
python run.py
```

Le backend sera sur `http://localhost:8082`

### 2. Démarrer le frontend Angular

```bash
cd easytess-frontend
ng serve
```

Le frontend sera sur `http://localhost:4200`

### 3. Ouvrir dans le navigateur

Allez sur `http://localhost:4200`

## 🎨 Captures d'écran

### Onglet "Analyse OCR"
- Upload d'image
- Sélection d'entité
- Analyse automatique
- Résultats avec statistiques

### Onglet "Créer une entité"
- Upload d'image de référence
- Dessin de zones sur canvas
- Sauvegarde de l'entité

## 🔧 Configuration

### Changer l'URL de l'API

Dans chaque service (`services/*.service.ts`), modifiez :

```typescript
private apiUrl = 'http://localhost:8082/api';
```

Ou créez un fichier `environment.ts` :

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8082/api'
};
```

Puis dans les services :
```typescript
import { environment } from '../environments/environment';

private apiUrl = environment.apiUrl;
```

## 📱 Build pour production

```bash
ng build --configuration production
```

Les fichiers seront dans `dist/easytess-frontend/`

Pour servir en production :
```bash
npm install -g http-server
cd dist/easytess-frontend
http-server -p 4200
```

## 🐛 Troubleshooting

### Erreur CORS
Assurez-vous que Flask-CORS est activé dans le backend :
```python
from flask_cors import CORS
CORS(app)
```

### Module non trouvé
Vérifiez que les imports sont corrects :
```typescript
import { OcrUploadComponent } from './components/ocr-upload.component';
```

### Backend non accessible
Vérifiez que le backend Flask tourne sur le port 8082 :
```bash
curl http://localhost:8082
```

## 📚 Ressources

- [Angular Documentation](https://angular.dev)
- [Angular Signals](https://angular.dev/guide/signals)
- [Standalone Components](https://angular.dev/guide/components/importing)

## 🎓 Prochaines étapes

1. Ajouter l'authentification
2. Créer un composant de liste des entités
3. Ajouter la gestion des erreurs globale
4. Implémenter le routing
5. Ajouter des tests unitaires

## 💡 Astuces

- Utilisez `ng generate component` pour créer de nouveaux composants
- Activez le mode debug dans les DevTools pour voir les requêtes HTTP
- Utilisez Angular DevTools extension pour inspecter les signals
