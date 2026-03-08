// app.component.ts - Composant principal avec onglets
// NOTE: Les chemins d'import dépendent de votre structure de projet
// Si vous copiez ce fichier dans src/app/, ajustez les chemins selon votre structure
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

// Option 1: Si vous avez copié les composants dans src/app/components/
// import { OcrUploadComponent } from './components/ocr-upload.component';
// import { EntityCreatorComponent } from './components/entity-creator.component';

// Option 2: Imports relatifs depuis example-app vers le dossier parent
import { OcrUploadComponent } from '../components/ocr-upload.component';
import { EntityCreatorComponent } from '../components/entity-creator.component';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, OcrUploadComponent, EntityCreatorComponent],
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
    title = 'EasyTess OCR';
    activeTab = signal<'ocr' | 'entity'>('ocr');

    setActiveTab(tab: 'ocr' | 'entity') {
        this.activeTab.set(tab);
    }
}
