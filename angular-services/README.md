# Services Angular pour EasyTess API

Ce dossier contient les services TypeScript Angular pour consommer l'API EasyTess.

## Installation

1. **Copiez les fichiers** dans votre projet Angular :
   ```
   src/app/services/
   ```

2. **Importez HttpClientModule** dans votre `app.module.ts` :
   ```typescript
   import { HttpClientModule } from '@angular/common/http';

   @NgModule({
     imports: [
       HttpClientModule,
       // ... autres imports
     ]
   })
   ```

## Utilisation

### 1. Upload et Analyse OCR

```typescript
import { Component } from '@angular/core';
import { FileService } from './services/file.service';
import { OcrService } from './services/ocr.service';

export class AnalyseComponent {
  constructor(
    private fileService: FileService,
    private ocrService: OcrService
  ) {}

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    
    // 1. Upload de l'image
    this.fileService.uploadImage(file).subscribe(response => {
      console.log('Image uploadée:', response.saved_filename);
      
      // 2. Analyse OCR
      this.ocrService.analyserImage(response.saved_filename).subscribe(result => {
        console.log('Résultats OCR:', result.resultats);
        console.log('Alertes:', result.alertes);
        console.log('Stats moteurs:', result.stats_moteurs);
      });
    });
  }
}
```

### 2. Créer une Entité avec Zones

```typescript
import { Component } from '@angular/core';
import { EntityService } from './services/entity.service';
import { Zone } from './services/models';

export class CreerEntiteComponent {
  zones: Zone[] = [];
  imageFilename: string = '';

  constructor(private entityService: EntityService) {}

  // 1. Upload image de référence
  onImageSelected(event: any) {
    const file: File = event.target.files[0];
    this.entityService.uploadImageEntite(file).subscribe(response => {
      this.imageFilename = response.filename;
      console.log('Dimensions:', response.dimensions);
    });
  }

  // 2. Ajouter une zone (depuis un canvas par exemple)
  ajouterZone(nom: string, coords: [number, number, number, number]) {
    this.zones.push({
      id: this.zones.length + 1,
      nom: nom,
      coords: coords
    });
  }

  // 3. Sauvegarder l'entité
  sauvegarder() {
    this.entityService.sauvegarderEntite(
      'Facture EDF',
      this.zones,
      this.imageFilename,
      'Modèle de facture EDF'
    ).subscribe(response => {
      console.log('Entité sauvegardée !');
    });
  }
}
```

### 3. Lister et Utiliser les Entités

```typescript
import { Component, OnInit } from '@angular/core';
import { EntityService } from './services/entity.service';
import { Entite } from './services/models';

export class EntitesComponent implements OnInit {
  entites: Entite[] = [];

  constructor(private entityService: EntityService) {}

  ngOnInit() {
    // Charger toutes les entités
    this.entityService.listerEntites().subscribe(entites => {
      this.entites = entites;
    });
  }

  // Activer une entité pour l'analyse
  activerEntite(nom: string) {
    this.entityService.setEntiteActive(nom).subscribe(response => {
      console.log('Entité active:', response.active);
    });
  }
}
```

### 4. Analyse avec Zones Personnalisées

```typescript
// Analyser avec des zones définies dynamiquement (sans entité)
const zonesCustom = {
  "Date": { "coords": [100, 50, 300, 100] },
  "Montant": { "coords": [100, 200, 300, 250] }
};

this.ocrService.analyserImage('mon_fichier.jpg', zonesCustom).subscribe(result => {
  console.log('Résultats:', result.resultats);
});
```

### 5. Export JSON

```typescript
import { FileService } from './services/file.service';

export class ExportComponent {
  constructor(private fileService: FileService) {}

  exporterResultats() {
    this.fileService.downloadJsonFile().subscribe(blob => {
      // Télécharger le fichier
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resultats.json';
      a.click();
    });
  }
}
```

## Configuration

Par défaut, l'API est configurée sur `http://localhost:8082`. 

Pour changer l'URL de base, modifiez la propriété `apiUrl` dans chaque service, ou créez un service de configuration centralisé :

```typescript
// config.service.ts
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  readonly API_URL = 'http://localhost:8082/api';
}
```

Puis injectez-le dans vos services.

## CORS

Assurez-vous que Flask-CORS est bien configuré côté backend (déjà fait dans votre API).

## Types TypeScript

Tous les types sont définis dans `models.ts` :
- `Zone` : Définition d'une zone OCR
- `Entite` : Modèle d'entité avec zones
- `ResultatOCR` : Résultat d'analyse OCR
- `AnalyseResponse` : Réponse complète d'analyse
- `UploadResponse` : Réponse d'upload
