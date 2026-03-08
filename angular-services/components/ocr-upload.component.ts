// ocr-upload.component.ts
import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FileService } from '../file.service';
import { OcrService } from '../ocr.service';
import { EntityService } from '../entity.service';
import { AnalyseResponse, Entite } from '../models';

@Component({
    selector: 'app-ocr-upload',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './ocr-upload.component.html',
    styleUrls: ['./ocr-upload.component.css']
})
export class OcrUploadComponent {
    private fileService = inject(FileService);
    private ocrService = inject(OcrService);
    private entityService = inject(EntityService);

    // Signals (Angular 18+)
    selectedFile = signal<File | null>(null);
    uploadedFilename = signal<string>('');
    imageUrl = signal<string>('');
    isUploading = signal<boolean>(false);
    isAnalyzing = signal<boolean>(false);
    analyseResults = signal<AnalyseResponse | null>(null);
    entites = signal<Entite[]>([]);
    selectedEntite = signal<string>('none');
    errorMessage = signal<string>('');

    ngOnInit() {
        this.loadEntites();
    }

    loadEntites() {
        this.entityService.listerEntites().subscribe({
            next: (entites) => this.entites.set(entites),
            error: (err) => console.error('Erreur chargement entités:', err)
        });
    }

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            this.selectedFile.set(file);
            this.errorMessage.set('');

            // Preview
            const reader = new FileReader();
            reader.onload = (e) => {
                this.imageUrl.set(e.target?.result as string);
            };
            reader.readAsDataURL(file);
        }
    }

    uploadImage() {
        const file = this.selectedFile();
        if (!file) {
            this.errorMessage.set('Veuillez sélectionner une image');
            return;
        }

        this.isUploading.set(true);
        this.errorMessage.set('');

        this.fileService.uploadImage(file).subscribe({
            next: (response) => {
                this.uploadedFilename.set(response.saved_filename);
                this.imageUrl.set(this.fileService.getImageUrl(response.saved_filename));
                this.isUploading.set(false);
                console.log('✅ Image uploadée:', response.saved_filename);
            },
            error: (err) => {
                this.errorMessage.set('Erreur lors de l\'upload: ' + err.message);
                this.isUploading.set(false);
            }
        });
    }

    analyser() {
        const filename = this.uploadedFilename();
        if (!filename) {
            this.errorMessage.set('Veuillez d\'abord uploader une image');
            return;
        }

        this.isAnalyzing.set(true);
        this.errorMessage.set('');

        // Activer l'entité si sélectionnée
        const entiteNom = this.selectedEntite();
        if (entiteNom !== 'none') {
            this.entityService.setEntiteActive(entiteNom).subscribe({
                next: () => {
                    this.performAnalyse(filename);
                },
                error: (err) => {
                    console.error('Erreur activation entité:', err);
                    this.performAnalyse(filename);
                }
            });
        } else {
            this.performAnalyse(filename);
        }
    }

    private performAnalyse(filename: string) {
        this.ocrService.analyserImage(filename).subscribe({
            next: (response) => {
                this.analyseResults.set(response);
                this.isAnalyzing.set(false);
                console.log('✅ Analyse terminée:', response);
            },
            error: (err) => {
                this.errorMessage.set('Erreur lors de l\'analyse: ' + err.message);
                this.isAnalyzing.set(false);
            }
        });
    }

    getResultatsArray() {
        const results = this.analyseResults();
        if (!results) return [];
        return Object.entries(results.resultats).map(([zone, data]) => ({
            zone,
            ...data
        }));
    }

    getStatutClass(statut: string): string {
        switch (statut) {
            case 'ok': return 'statut-ok';
            case 'faible_confiance': return 'statut-warning';
            case 'echec': return 'statut-error';
            default: return '';
        }
    }

    exportResults() {
        this.fileService.downloadJsonFile().subscribe({
            next: (blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `resultats_${Date.now()}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            },
            error: (err) => {
                this.errorMessage.set('Erreur lors de l\'export: ' + err.message);
            }
        });
    }

    reset() {
        this.selectedFile.set(null);
        this.uploadedFilename.set('');
        this.imageUrl.set('');
        this.analyseResults.set(null);
        this.errorMessage.set('');
    }
}
