// ocr-upload.component.ts - Simplifié pour l'analyse uniquement
import { Component, signal, inject, ViewChild, ElementRef, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FileService } from '../services/file.service';
import { OcrService } from '../services/ocr.service';
import { EntityService } from '../services/entity.service';
import { AnalyseResponse, Entite, UploadResponse } from '../services/models';

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

    @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    private ctx: CanvasRenderingContext2D | null = null;
    private currentImage: HTMLImageElement | null = null;
    private scale = 1;

    // Signals
    selectedFile = signal<File | null>(null);
    uploadedFilename = signal<string>('');
    imageUrl = signal<string>('');
    isUploading = signal<boolean>(false);
    isAnalyzing = signal<boolean>(false);
    analyseResults = signal<AnalyseResponse | null>(null);
    entites = signal<Entite[]>([]);
    selectedEntite = signal<string>('none');
    errorMessage = signal<string>('');

    constructor() {
        effect(() => {
            const entite = this.selectedEntite();
            const img = this.imageUrl();
            if (img && this.currentImage) {
                setTimeout(() => this.drawCanvas(), 50);
            }
        });
    }

    ngOnInit() {
        this.loadEntites();
    }

    loadEntites() {
        this.entityService.listerEntites().subscribe({
            next: (entites: Entite[]) => this.entites.set(entites),
            error: (err: any) => console.error('Erreur chargement entités:', err)
        });
    }

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            this.selectedFile.set(file);
            this.errorMessage.set('');

            if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
                // PDF: Pas de prévisualisation locale immédiate
                this.imageUrl.set('');
                this.currentImage = null;
            } else {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const url = e.target?.result as string;
                    this.imageUrl.set(url);

                    const img = new Image();
                    img.onload = () => {
                        this.currentImage = img;
                        this.drawCanvas();
                    };
                    img.src = url;
                };
                reader.readAsDataURL(file);
            }
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
            next: (response: UploadResponse) => {
                this.uploadedFilename.set(response.saved_filename);
                const newImageUrl = this.fileService.getImageUrl(response.saved_filename);
                this.imageUrl.set(newImageUrl);
                this.isUploading.set(false);
                console.log('✅ Image uploadée:', response.saved_filename);

                const img = new Image();
                img.onload = () => {
                    this.currentImage = img;
                    this.drawCanvas();
                };
                img.src = newImageUrl;
            },
            error: (err: any) => {
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

        const entiteNom = this.selectedEntite();
        let zonesConfig: any = null;
        let cadre_reference: any = null;

        if (entiteNom !== 'none') {
            const entite = this.entites().find(e => e.nom === entiteNom);
            if (entite && entite.zones && entite.zones.length > 0) {
                zonesConfig = {};
                entite.zones.forEach(z => {
                    zonesConfig[z.nom] = {
                        coords: z.coords,
                        type: z.type || 'text',
                        lang: z.lang || 'ara+fra',
                        preprocess: z.preprocess || 'auto'
                    };
                });
                console.log('✅ Zones configurées pour API:', zonesConfig);

                // NOUVEAU: Récupérer le cadre de référence si défini
                if (entite.cadre_reference) {
                    cadre_reference = entite.cadre_reference;
                    console.log('📐 Cadre de référence activé:', cadre_reference);
                }
            }
        }

        this.performAnalyse(filename, zonesConfig, cadre_reference);
    }

    private performAnalyse(filename: string, zones?: any, cadre_reference?: any) {
        this.ocrService.analyserImage(filename, zones, cadre_reference).subscribe({
            next: (response: AnalyseResponse) => {
                this.analyseResults.set(response);
                this.isAnalyzing.set(false);
                console.log('✅ Analyse terminée:', response);
                // Redessiner le canvas avec les résultats
                setTimeout(() => this.drawCanvas(), 100);
            },
            error: (err: any) => {
                this.errorMessage.set('Erreur lors de l\'analyse: ' + err.message);
                this.isAnalyzing.set(false);
            }
        });
    }

    drawCanvas(retryCount = 0) {
        if (!this.canvasRef) {
            if (retryCount < 10) {
                setTimeout(() => this.drawCanvas(retryCount + 1), 100);
            }
            return;
        }
        if (!this.currentImage) return;

        const canvas = this.canvasRef.nativeElement;
        this.ctx = canvas.getContext('2d');
        if (!this.ctx) return;

        const img = this.currentImage;
        const maxWidth = 800;
        this.scale = Math.min(1, maxWidth / img.width);
        canvas.width = img.width * this.scale;
        canvas.height = img.height * this.scale;

        this.ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        // MODE 1: AFFICHER RÉSULTATS ANALYSE (Si disponibles)
        const results = this.analyseResults();
        if (results && results.resultats) {
            Object.entries(results.resultats).forEach(([nom, data]: [string, any]) => {
                if (data.coords) {
                    let [x1, y1, x2, y2] = data.coords;
                    // Les coords venant du backend (post-fix) sont normalisées IMAGE (0-1)

                    // Sécurité types
                    x1 = Number(x1); y1 = Number(y1);
                    x2 = Number(x2); y2 = Number(y2);

                    const sx1 = x1 * img.width * this.scale;
                    const sy1 = y1 * img.height * this.scale;
                    const w = (x2 - x1) * img.width * this.scale;
                    const h = (y2 - y1) * img.height * this.scale;

                    this.ctx!.lineWidth = 2;
                    this.ctx!.strokeStyle = '#0066cc'; // Bleu pour résultats
                    this.ctx!.strokeRect(sx1, sy1, w, h);

                    // Texte
                    this.ctx!.fillStyle = '#0066cc';
                    const textWidth = this.ctx!.measureText(nom).width;
                    this.ctx!.fillRect(sx1, sy1 - 20, textWidth + 10, 20);
                    this.ctx!.fillStyle = 'white';
                    this.ctx!.font = '14px Arial';
                    this.ctx!.fillText(nom, sx1 + 5, sy1 - 5);
                }
            });
            return;
        }

        // MODE 2: PREVIEW DÉFINITION ENTITÉ (Fallback)
        // Attention: Affiche les zones relatives au cadre comme si c'était l'image (0,0)
        // Car on ne connait pas encore la position du cadre.
        const entiteNom = this.selectedEntite();
        if (entiteNom !== 'none') {
            const entite = this.entites().find(e => e.nom === entiteNom);
            if (entite && entite.zones) {
                this.ctx.lineWidth = 2;
                this.ctx.font = '14px Arial';

                entite.zones.forEach(zone => {
                    let [x1, y1, x2, y2] = zone.coords;

                    // Handle relative coords
                    if (x1 <= 1.0 && y1 <= 1.0 && x2 <= 1.0 && y2 <= 1.0) {
                        x1 *= img.width;
                        y1 *= img.height;
                        x2 *= img.width;
                        y2 *= img.height;
                    }

                    const sx1 = x1 * this.scale;
                    const sy1 = y1 * this.scale;
                    const w = (x2 - x1) * this.scale;
                    const h = (y2 - y1) * this.scale;

                    this.ctx!.strokeStyle = '#00ff00'; // Vert pour définition
                    this.ctx!.strokeRect(sx1, sy1, w, h);
                    this.ctx!.fillStyle = 'rgba(0, 255, 0, 0.2)';
                    this.ctx!.fillRect(sx1, sy1, w, h);

                    this.ctx!.fillStyle = 'black';
                    const textWidth = this.ctx!.measureText(zone.nom).width;
                    this.ctx!.fillRect(sx1, sy1 - 20, textWidth + 10, 20);
                    this.ctx!.fillStyle = 'white';
                    this.ctx!.fillText(zone.nom, sx1 + 5, sy1 - 5);
                });
            }
        }
    }

    getResultatsArray() {
        const results = this.analyseResults();
        if (!results) return [];
        return Object.entries(results.resultats).map(([zone, data]) => ({
            zone,
            ...(data as any)
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
        const results = this.analyseResults();
        const filename = this.uploadedFilename();

        const exportData = {
            filename: filename,
            resultats: results?.resultats || {}
        };

        this.fileService.downloadJsonFile(exportData).subscribe({
            next: (blob: Blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `resultats_${Date.now()}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            },
            error: (err: any) => {
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
        this.currentImage = null;
        if (this.canvasRef && this.ctx) {
            this.ctx.clearRect(0, 0, this.canvasRef.nativeElement.width, this.canvasRef.nativeElement.height);
        }
    }
}
