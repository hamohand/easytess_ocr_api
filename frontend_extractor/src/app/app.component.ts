// app.component.ts - Composant principal pour de l'Extraction
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentExtractorComponent } from './components/document-extractor.component';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, DocumentExtractorComponent],
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
    title = 'EasyTess - Extraction';
}
