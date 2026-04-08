// app.component.ts - Composant principal pour EasyTess OCR
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OcrUploadComponent } from './components/ocr-upload.component';
import { EntityCreatorComponent } from './components/entity-creator.component';
import { CompositeCreatorComponent } from './components/composite-creator/composite-creator.component';
import { MatchingComponent } from './components/matching/matching.component';

type OcrTab = 'analyse' | 'entity' | 'composite' | 'matching';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, OcrUploadComponent, EntityCreatorComponent, CompositeCreatorComponent, MatchingComponent],
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
    title = 'EasyTess - OCR';
    activeOcrTab = signal<OcrTab>('analyse');

    setOcrTab(tab: OcrTab) {
        this.activeOcrTab.set(tab);
    }
}
