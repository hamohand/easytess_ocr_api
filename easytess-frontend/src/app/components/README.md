# Composants Angular pour EasyTess API

Ce dossier contient des composants standalone Angular 18+ prêts à l'emploi.

## 📦 Composants inclus

### 1. **OcrUploadComponent** - Analyse OCR
Composant complet pour uploader une image et l'analyser avec OCR.

**Fonctionnalités :**
- Upload d'image avec preview
- Sélection d'entité (modèle de zones)
- Analyse OCR (Tesseract + EasyOCR)
- Affichage des résultats avec statistiques
- Export JSON
- Design moderne et responsive

**Utilisation :**
```typescript
import { OcrUploadComponent } from './components/ocr-upload.component';

@Component({
  standalone: true,
  imports: [OcrUploadComponent],
  template: '<app-ocr-upload></app-ocr-upload>'
})
export class AppComponent {}
```

### 2. **EntityCreatorComponent** - Créateur d'entités
Composant interactif pour créer des entités OCR en dessinant des zones sur une image.

**Fonctionnalités :**
- Upload d'image de référence
- Dessin de zones sur canvas (clic + glisser)
- Nommage des zones
- Liste des zones créées
- Sauvegarde de l'entité
- Interface intuitive

**Utilisation :**
```typescript
import { EntityCreatorComponent } from './components/entity-creator.component';

@Component({
  standalone: true,
  imports: [EntityCreatorComponent],
  template: '<app-entity-creator></app-entity-creator>'
})
export class AppComponent {}
```

## 🚀 Installation

### 1. Copiez les fichiers dans votre projet Angular

```
src/app/
├── services/
│   ├── models.ts
│   ├── ocr.service.ts
│   ├── entity.service.ts
│   ├── file.service.ts
│   └── index.ts
└── components/
    ├── ocr-upload.component.ts
    ├── ocr-upload.component.html
    ├── ocr-upload.component.css
    ├── entity-creator.component.ts
    ├── entity-creator.component.html
    └── entity-creator.component.css
```

### 2. Configuration de l'application

**app.config.ts** (Angular 18+) :
```typescript
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient()
  ]
};
```

**main.ts** :
```typescript
import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

bootstrapApplication(AppComponent, appConfig)
  .catch((err) => console.error(err));
```

### 3. Exemple d'application complète

**app.component.ts** :
```typescript
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OcrUploadComponent } from './components/ocr-upload.component';
import { EntityCreatorComponent } from './components/entity-creator.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, OcrUploadComponent, EntityCreatorComponent],
  template: `
    <div class="app-container">
      <nav class="tabs">
        <button 
          [class.active]="activeTab() === 'ocr'"
          (click)="activeTab.set('ocr')">
          🔍 Analyse OCR
        </button>
        <button 
          [class.active]="activeTab() === 'entity'"
          (click)="activeTab.set('entity')">
          🎨 Créer une entité
        </button>
      </nav>

      <div class="content">
        @if (activeTab() === 'ocr') {
          <app-ocr-upload />
        } @else {
          <app-entity-creator />
        }
      </div>
    </div>
  `,
  styles: [`
    .app-container {
      min-height: 100vh;
      background: #f5f5f5;
    }

    .tabs {
      background: white;
      border-bottom: 2px solid #dee2e6;
      display: flex;
      gap: 0;
      padding: 0 2rem;
    }

    .tabs button {
      padding: 1rem 2rem;
      border: none;
      background: transparent;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 500;
      color: #6c757d;
      border-bottom: 3px solid transparent;
      transition: all 0.3s;
    }

    .tabs button:hover {
      color: #007bff;
    }

    .tabs button.active {
      color: #007bff;
      border-bottom-color: #007bff;
    }

    .content {
      padding: 2rem;
    }
  `]
})
export class AppComponent {
  activeTab = signal<'ocr' | 'entity'>('ocr');
}
```

## 🎨 Fonctionnalités Angular 18+

Les composants utilisent les dernières fonctionnalités d'Angular :

### ✅ Standalone Components
```typescript
@Component({
  standalone: true,
  imports: [CommonModule, FormsModule]
})
```

### ✅ Signals
```typescript
selectedFile = signal<File | null>(null);
isUploading = signal<boolean>(false);
```

### ✅ inject() function
```typescript
private fileService = inject(FileService);
private ocrService = inject(OcrService);
```

### ✅ Control Flow (@if, @for)
```html
@if (imageUrl()) {
  <img [src]="imageUrl()" />
}

@for (zone of zones(); track zone.id) {
  <div>{{ zone.nom }}</div>
}
```

## 🎯 Workflow complet

### Scénario 1 : Créer une entité puis analyser

1. **Créer une entité** (EntityCreatorComponent)
   - Upload une image de référence (ex: facture vierge)
   - Dessiner des zones (Date, Montant, Client...)
   - Sauvegarder l'entité

2. **Analyser un document** (OcrUploadComponent)
   - Sélectionner l'entité créée
   - Upload un nouveau document du même type
   - Lancer l'analyse OCR
   - Les zones définies seront automatiquement analysées

### Scénario 2 : Analyse rapide sans entité

1. Upload une image
2. Lancer l'analyse (utilise une zone par défaut)
3. Voir les résultats

## 🔧 Personnalisation

### Changer l'URL de l'API

Modifiez `apiUrl` dans chaque service :
```typescript
private apiUrl = 'http://votre-serveur:8082/api';
```

Ou créez un service de configuration centralisé.

### Personnaliser les styles

Tous les composants ont leur propre fichier CSS. Vous pouvez :
- Modifier les couleurs
- Ajuster les espacements
- Changer les animations

## 📱 Responsive Design

Les composants sont entièrement responsive et s'adaptent aux mobiles, tablettes et desktop.

## 🐛 Debugging

Pour activer les logs de debug :
```typescript
// Dans les composants
console.log('État actuel:', this.analyseResults());
```

## 🚀 Déploiement

Pour builder l'application :
```bash
ng build --configuration production
```

Les fichiers seront dans `dist/`.

## 📝 Notes importantes

1. **CORS** : Assurez-vous que Flask-CORS est activé côté backend
2. **Session** : L'API utilise encore des sessions pour certaines fonctionnalités (compatibilité)
3. **Fichiers** : Les images uploadées sont stockées dans `uploads/` côté backend

## 🎓 Exemples d'utilisation avancée

### Utiliser les services directement

```typescript
import { inject } from '@angular/core';
import { OcrService, EntityService } from './services';

export class MyComponent {
  private ocrService = inject(OcrService);
  private entityService = inject(EntityService);

  analyserCustom() {
    const zones = {
      "Titre": { "coords": [100, 50, 400, 100] },
      "Corps": { "coords": [100, 150, 400, 400] }
    };

    this.ocrService.analyserImage('mon_fichier.jpg', zones)
      .subscribe(result => {
        console.log(result.resultats);
      });
  }
}
```

## 📚 Ressources

- [Documentation Angular](https://angular.dev)
- [Angular Signals](https://angular.dev/guide/signals)
- [Standalone Components](https://angular.dev/guide/components/importing)
