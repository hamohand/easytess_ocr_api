// ocr-upload.component.ts - Analyse simple et batch (async avec SSE)
import { Component, signal, inject, ViewChild, ElementRef, effect, OnDestroy, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FileService } from '../services/file.service';
import { OcrService } from '../services/ocr.service';
import { EntityService } from '../services/entity.service';
import { AnalyseResponse, Entite, UploadResponse, BatchAnalyseResponse, BatchFileResult } from '../services/models';

@Component({
    selector: 'app-ocr-upload',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './ocr-upload.component.html',
    styleUrls: ['./ocr-upload.component.css']
})
export class OcrUploadComponent implements OnDestroy {
    private fileService = inject(FileService);
    private ocrService = inject(OcrService);
    private entityService = inject(EntityService);
    private ngZone = inject(NgZone);

    @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    private ctx: CanvasRenderingContext2D | null = null;
    private currentImage: HTMLImageElement | null = null;
    private scale = 1;
    private eventSource: EventSource | null = null;

    // Mode toggle: 'single' | 'multi' | 'folder'
    activeMode = signal<'single' | 'multi' | 'folder'>('single');

    // Signals - Single mode
    selectedFile = signal<File | null>(null);
    uploadedFilename = signal<string>('');
    imageUrl = signal<string>('');
    isUploading = signal<boolean>(false);
    isAnalyzing = signal<boolean>(false);
    analyseResults = signal<AnalyseResponse | null>(null);
    entites = signal<Entite[]>([]);
    selectedEntite = signal<string>('none');
    errorMessage = signal<string>('');

    // Signals - Batch mode (multi + folder)
    selectedFiles = signal<File[]>([]);
    uploadedBatchFilenames = signal<string[]>([]);
    batchResults = signal<BatchAnalyseResponse | null>(null);
    expandedFileIndex = signal<number | null>(null);

    // Signals - Corrections
    corrections = signal<Record<string, string>>({});
    isSavingCorrections = signal<boolean>(false);

    // Signals - Async progress
    batchProgress = signal<{ completed: number; total: number; currentFile: string } | null>(null);

    // Signals - Analysis mode
    analysisMode = signal<'rapide' | 'approfondi'>('rapide');

    // Signals - Synthesis dashboard
    showOnlyDouteux = signal<boolean>(false);
    batchCorrections = signal<Record<string, Record<string, string>>>({});

    // Signals - Folder mode (server-side)
    folderPath = signal<string>('');

    constructor() {
        effect(() => {
            const entite = this.selectedEntite();
            const img = this.imageUrl();
            if (img && this.currentImage) {
                setTimeout(() => this.drawCanvas(), 50);
            }
        });
    }

    ngOnDestroy() {
        this.closeEventSource();
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

    setMode(mode: 'single' | 'multi' | 'folder') {
        this.reset();
        this.activeMode.set(mode);
    }

    private closeEventSource() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }

    private buildZonesConfig(): { zonesConfig: any; cadre_reference: any } {
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
                        preprocess: z.preprocess || 'auto',
                        char_filter: z.char_filter || 'none',
                        margin: z.margin || 0,
                        expected_format: z.expected_format || 'auto',
                        valeurs_attendues: z.valeurs_attendues || []
                    };
                });

                if (entite.cadre_reference) {
                    cadre_reference = entite.cadre_reference;
                }
            }
        }
        return { zonesConfig, cadre_reference };
    }

    // =============================================
    // SINGLE FILE MODE
    // =============================================

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            this.selectedFile.set(file);
            this.errorMessage.set('');

            if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
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
        const { zonesConfig, cadre_reference } = this.buildZonesConfig();
        this.performAnalyse(filename, zonesConfig, cadre_reference);
    }

    private performAnalyse(filename: string, zones?: any, cadre_reference?: any) {
        this.ocrService.analyserImage(filename, zones, cadre_reference, this.analysisMode()).subscribe({
            next: (response: AnalyseResponse) => {
                this.analyseResults.set(response);
                this.isAnalyzing.set(false);
                console.log('✅ Analyse terminée:', response);
                setTimeout(() => this.drawCanvas(), 100);
            },
            error: (err: any) => {
                this.errorMessage.set('Erreur lors de l\'analyse: ' + err.message);
                this.isAnalyzing.set(false);
            }
        });
    }

    // =============================================
    // MULTI-FILE BATCH MODE (upload + async)
    // =============================================

    onMultiFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const files = Array.from(input.files).filter(f => {
                const ext = f.name.toLowerCase();
                return ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.png')
                    || ext.endsWith('.bmp') || ext.endsWith('.tiff') || ext.endsWith('.pdf');
            });
            this.selectedFiles.set(files);
            this.errorMessage.set('');
        }
    }

    uploadBatch() {
        const files = this.selectedFiles();
        if (files.length === 0) {
            this.errorMessage.set('Veuillez sélectionner des fichiers');
            return;
        }

        this.isUploading.set(true);
        this.errorMessage.set('');

        this.fileService.uploadMultipleImages(files).subscribe({
            next: (response) => {
                const validFiles = response.files
                    .filter(f => f.saved_filename)
                    .map(f => f.saved_filename);
                this.uploadedBatchFilenames.set(validFiles);
                this.isUploading.set(false);
                console.log(`✅ ${validFiles.length} fichiers uploadés`);
            },
            error: (err: any) => {
                this.errorMessage.set('Erreur lors de l\'upload batch: ' + err.message);
                this.isUploading.set(false);
            }
        });
    }

    analyserBatch() {
        const filenames = this.uploadedBatchFilenames();
        if (filenames.length === 0) {
            this.errorMessage.set('Veuillez d\'abord uploader des fichiers');
            return;
        }

        this.isAnalyzing.set(true);
        this.errorMessage.set('');
        this.batchProgress.set({ completed: 0, total: filenames.length, currentFile: '' });

        const { zonesConfig, cadre_reference } = this.buildZonesConfig();

        // Async batch with SSE progress
        this.ocrService.analyserBatchAsync(filenames, zonesConfig, cadre_reference, this.analysisMode()).subscribe({
            next: (response) => {
                console.log('✅ Job batch lancé:', response.job_id);
                this.listenToProgress(response.job_id);
            },
            error: (err: any) => {
                this.errorMessage.set('Erreur lors du lancement batch: ' + err.message);
                this.isAnalyzing.set(false);
                this.batchProgress.set(null);
            }
        });
    }

    private listenToProgress(jobId: string) {
        this.closeEventSource();
        const eventSource = this.ocrService.connectBatchProgress(jobId);
        this.eventSource = eventSource;

        eventSource.onmessage = (event) => {
            this.ngZone.run(() => {
                const data = JSON.parse(event.data);

                if (data.error) {
                    this.errorMessage.set('Erreur SSE: ' + data.error);
                    this.isAnalyzing.set(false);
                    this.batchProgress.set(null);
                    this.closeEventSource();
                    return;
                }

                this.batchProgress.set({
                    completed: data.completed,
                    total: data.total,
                    currentFile: data.current_file
                });

                if (data.status === 'done') {
                    this.batchResults.set({
                        success: true,
                        total: data.total,
                        reussis: data.reussis,
                        echoues: data.echoues,
                        resultats_batch: data.resultats_batch
                    });
                    this.isAnalyzing.set(false);
                    this.batchProgress.set(null);
                    this.closeEventSource();
                    console.log('✅ Analyse batch async terminée');
                }
            });
        };

        eventSource.onerror = () => {
            this.ngZone.run(() => {
                // Fallback to polling if SSE fails
                this.closeEventSource();
                this.pollBatchResult(jobId);
            });
        };
    }

    private pollBatchResult(jobId: string) {
        const interval = setInterval(() => {
            this.ocrService.getBatchResult(jobId).subscribe({
                next: (data) => {
                    this.batchProgress.set({
                        completed: data.completed,
                        total: data.total,
                        currentFile: data.current_file
                    });

                    if (data.status === 'done') {
                        clearInterval(interval);
                        this.batchResults.set({
                            success: true,
                            total: data.total,
                            reussis: data.reussis,
                            echoues: data.echoues,
                            resultats_batch: data.resultats_batch
                        });
                        this.isAnalyzing.set(false);
                        this.batchProgress.set(null);
                    }
                },
                error: () => {
                    clearInterval(interval);
                    this.errorMessage.set('Erreur lors du suivi de la progression');
                    this.isAnalyzing.set(false);
                    this.batchProgress.set(null);
                }
            });
        }, 1000);
    }

    // =============================================
    // FOLDER MODE (upload à plat via webkitdirectory)
    // =============================================

    onFolderSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const files = Array.from(input.files).filter(f => {
                const ext = f.name.toLowerCase();
                return ext.endsWith('.jpg') || ext.endsWith('.jpeg') || ext.endsWith('.png')
                    || ext.endsWith('.bmp') || ext.endsWith('.tiff') || ext.endsWith('.pdf');
            });
            this.selectedFiles.set(files);
            this.errorMessage.set('');
            if (files.length === 0) {
                this.errorMessage.set('Aucun fichier image trouvé dans le dossier sélectionné');
            }
        }
    }

    // =============================================
    // SHARED UTILITIES
    // =============================================

    toggleFileDetail(index: number) {
        if (this.expandedFileIndex() === index) {
            this.expandedFileIndex.set(null);
        } else {
            this.expandedFileIndex.set(index);
        }
    }

    getFileResultatsArray(fileResult: BatchFileResult) {
        if (!fileResult.resultats) return [];
        return Object.entries(fileResult.resultats).map(([zone, data]) => ({
            zone,
            ...(data as any)
        }));
    }

    // =============================================
    // TABLEAU DE SYNTHÈSE (cas douteux batch)
    // =============================================

    /**
     * Extrait tous les cas douteux (confiance < 65% ou statut != ok) du batch.
     */
    getCasDouteuxBatch(): { filename: string; zone: string; texte_final: string; confiance_auto: number; statut: string; moteur: string }[] {
        const batch = this.batchResults();
        if (!batch || !batch.resultats_batch) return [];

        const cas: { filename: string; zone: string; texte_final: string; confiance_auto: number; statut: string; moteur: string }[] = [];

        for (const fileResult of batch.resultats_batch) {
            if (!fileResult.success || !fileResult.resultats) continue;
            for (const [zoneName, resultat] of Object.entries(fileResult.resultats)) {
                const r = resultat as any;
                if (r.statut !== 'ok' || r.confiance_auto < 0.65) {
                    cas.push({
                        filename: fileResult.filename,
                        zone: zoneName,
                        texte_final: r.texte_final || '',
                        confiance_auto: r.confiance_auto || 0,
                        statut: r.statut || 'echec',
                        moteur: r.moteur || 'inconnu'
                    });
                }
            }
        }
        return cas;
    }

    /**
     * Statistiques de synthèse du batch.
     */
    getBatchSynthStats(): { totalZones: number; ok: number; douteux: number; tauxReussite: number } {
        const batch = this.batchResults();
        if (!batch || !batch.resultats_batch) return { totalZones: 0, ok: 0, douteux: 0, tauxReussite: 0 };

        let totalZones = 0;
        let ok = 0;

        for (const fileResult of batch.resultats_batch) {
            if (!fileResult.success || !fileResult.resultats) continue;
            for (const resultat of Object.values(fileResult.resultats)) {
                totalZones++;
                const r = resultat as any;
                if (r.statut === 'ok' && r.confiance_auto >= 0.65) {
                    ok++;
                }
            }
        }

        const douteux = totalZones - ok;
        const tauxReussite = totalZones > 0 ? Math.round((ok / totalZones) * 100) : 0;
        return { totalZones, ok, douteux, tauxReussite };
    }

    /**
     * Met à jour une correction batch (par fichier + zone).
     */
    updateBatchCorrection(filename: string, zone: string, text: string) {
        this.batchCorrections.update(c => {
            const fileCopy = { ...(c[filename] || {}) };
            fileCopy[zone] = text;
            return { ...c, [filename]: fileCopy };
        });
    }

    /**
     * Retourne le texte corrigé ou le texte original pour une zone batch.
     */
    getBatchCorrectedText(filename: string, zone: string, original: string): string {
        const corr = this.batchCorrections();
        return corr[filename]?.[zone] ?? original;
    }

    /**
     * Nombre total de corrections batch en attente.
     */
    getBatchCorrectionsCount(): number {
        let count = 0;
        for (const file of Object.values(this.batchCorrections())) {
            count += Object.keys(file).length;
        }
        return count;
    }


    exportBatchResults() {
        const results = this.batchResults();
        if (!results) return;

        this.fileService.downloadBatchJsonFile(results.resultats_batch).subscribe({
            next: (blob: Blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `resultats_batch_${Date.now()}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            },
            error: (err: any) => {
                this.errorMessage.set('Erreur lors de l\'export: ' + err.message);
            }
        });
    }

    getProgressPercent(): number {
        const p = this.batchProgress();
        if (!p || p.total === 0) return 0;
        return Math.round((p.completed / p.total) * 100);
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

        const results = this.analyseResults();
        if (results && results.resultats) {
            const cadreDetecte = results.cadre_detecte; // {x, y, width, height} -> Image relative (0-1)

            // ─── TRACER LE CADRE DE L'ENTITÉ (vert, bien visible) ───
            if (cadreDetecte) {
                const cx = cadreDetecte.x * img.width * this.scale;
                const cy = cadreDetecte.y * img.height * this.scale;
                const cw = cadreDetecte.width * img.width * this.scale;
                const ch = cadreDetecte.height * img.height * this.scale;

                this.ctx!.save();
                this.ctx!.lineWidth = 3;
                this.ctx!.strokeStyle = '#00cc44';
                this.ctx!.setLineDash([10, 5]);
                this.ctx!.strokeRect(cx, cy, cw, ch);
                this.ctx!.setLineDash([]);

                // Label du cadre
                const label = `CADRE (${Math.round(cadreDetecte.width * img.width)}×${Math.round(cadreDetecte.height * img.height)}px)`;
                this.ctx!.font = 'bold 14px Arial';
                const labelW = this.ctx!.measureText(label).width;
                this.ctx!.fillStyle = 'rgba(0, 204, 68, 0.85)';
                this.ctx!.fillRect(cx, cy - 22, labelW + 12, 22);
                this.ctx!.fillStyle = 'white';
                this.ctx!.fillText(label, cx + 6, cy - 6);
                this.ctx!.restore();
            }

            // ─── TRACER LES ZONES (bleu) ───
            Object.entries(results.resultats).forEach(([nom, data]: [string, any]) => {
                if (data.coords) {
                    let [x1, y1, x2, y2] = data.coords;
                    x1 = Number(x1); y1 = Number(y1);
                    x2 = Number(x2); y2 = Number(y2);

                    // Si le backend a fourni le cadre détecté (qui sert d'origine 0,0),
                    // on reconvertit les coordonnées "cadre-relatives" en "image-relatives"
                    // juste pour dessiner correctement les carrés bleus sur l'image entière.
                    if (cadreDetecte) {
                        x1 = cadreDetecte.x + x1 * cadreDetecte.width;
                        y1 = cadreDetecte.y + y1 * cadreDetecte.height;
                        x2 = cadreDetecte.x + x2 * cadreDetecte.width;
                        y2 = cadreDetecte.y + y2 * cadreDetecte.height;
                    }

                    const sx1 = x1 * img.width * this.scale;
                    const sy1 = y1 * img.height * this.scale;
                    const w = (x2 - x1) * img.width * this.scale;
                    const h = (y2 - y1) * img.height * this.scale;

                    this.ctx!.lineWidth = 2;
                    this.ctx!.strokeStyle = '#0066cc';
                    this.ctx!.strokeRect(sx1, sy1, w, h);

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

        const entiteNom = this.selectedEntite();
        if (entiteNom !== 'none') {
            const entite = this.entites().find(e => e.nom === entiteNom);
            if (entite && entite.zones) {
                this.ctx.lineWidth = 2;
                this.ctx.font = '14px Arial';

                entite.zones.forEach(zone => {
                    let [nx1, ny1, nx2, ny2] = zone.coords;

                    // Convert frame-relative coordinates back to image-relative coordinates using cadre_reference
                    if (entite.cadre_reference) {
                        const cadre = entite.cadre_reference;
                        let cx = 0, cy = 0, cw = 1, ch = 1;

                        if (cadre.gauche && cadre.droite && cadre.haut && cadre.bas) {
                            cx = cadre.gauche.position_base[0];
                            cy = cadre.haut.position_base[1];
                            cw = Math.abs(cadre.droite.position_base[0] - cadre.gauche.position_base[0]);
                            ch = Math.abs(cadre.bas.position_base[1] - cadre.haut.position_base[1]);
                        } else if (cadre.origine && cadre.largeur && cadre.hauteur) {
                            cx = cadre.origine.position_base[0];
                            cy = cadre.origine.position_base[1];
                            cw = Math.abs(cadre.largeur.position_base[0] - cx);
                            ch = Math.abs(cadre.hauteur.position_base[1] - cy);
                        }

                        if (cw < 0.001) cw = 1;
                        if (ch < 0.001) ch = 1;

                        nx1 = nx1 * cw + cx;
                        ny1 = ny1 * ch + cy;
                        nx2 = nx2 * cw + cx;
                        ny2 = ny2 * ch + cy;
                    }

                    let x1 = nx1;
                    let y1 = ny1;
                    let x2 = nx2;
                    let y2 = ny2;

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

                    this.ctx!.strokeStyle = '#00ff00';
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
            case 'corrigé': return 'statut-ok';
            case 'faible_confiance': return 'statut-warning';
            case 'echec': return 'statut-error';
            default: return '';
        }
    }

    updateCorrection(zone: string, text: string) {
        this.corrections.update(c => ({...c, [zone]: text}));
    }

    sauvegarderCorrections() {
        const corr = this.corrections();
        if (Object.keys(corr).length === 0) return;
        
        this.isSavingCorrections.set(true);
        this.ocrService.sauvegarderCorrections(corr).subscribe({
            next: () => {
                this.isSavingCorrections.set(false);
                const res = this.analyseResults();
                if (res) {
                    for (const [zone, text] of Object.entries(corr)) {
                        if (res.resultats[zone]) {
                            res.resultats[zone].texte_auto = text;
                            res.resultats[zone].texte_final = text;
                            res.resultats[zone].statut = 'corrigé';
                        }
                    }
                    this.analyseResults.set({ ...res });
                }
                this.corrections.set({});
            },
            error: (err: any) => {
                this.isSavingCorrections.set(false);
                this.errorMessage.set('Erreur lors de la sauvegarde: ' + err.message);
            }
        });
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
        this.closeEventSource();
        // Single mode
        this.selectedFile.set(null);
        this.uploadedFilename.set('');
        this.imageUrl.set('');
        this.analyseResults.set(null);
        this.errorMessage.set('');
        this.currentImage = null;
        if (this.canvasRef && this.ctx) {
            this.ctx.clearRect(0, 0, this.canvasRef.nativeElement.width, this.canvasRef.nativeElement.height);
        }
        // Batch mode
        this.selectedFiles.set([]);
        this.uploadedBatchFilenames.set([]);
        this.batchResults.set(null);
        this.expandedFileIndex.set(null);
        this.batchProgress.set(null);
        // Folder mode
        // Corrections
        this.corrections.set({});
        this.isSavingCorrections.set(false);
        // Synthesis
        this.showOnlyDouteux.set(false);
        this.batchCorrections.set({});
    }

    // =============================================
    // CALIBRATION: Appliquer les marges optimales
    // =============================================

    /**
     * Retourne les zones dont la marge optimale (trouvée par approfondi) diffère de la config actuelle.
     */
    getMargesOptimales(): { zone: string; ancienne: number; nouvelle: number }[] {
        const results = this.analyseResults();
        if (!results || !results.resultats) return [];

        const entiteNom = this.selectedEntite();
        if (entiteNom === 'none') return [];

        const entite = this.entites().find(e => e.nom === entiteNom);
        if (!entite || !entite.zones) return [];

        const suggestions: { zone: string; ancienne: number; nouvelle: number }[] = [];

        for (const [zoneName, resultat] of Object.entries(results.resultats)) {
            if (resultat.marge_utilisee === undefined) continue;

            const zoneConfig = entite.zones.find(z => z.nom === zoneName);
            const ancienneMarge = zoneConfig?.margin || 0;

            if (resultat.marge_utilisee !== ancienneMarge) {
                suggestions.push({
                    zone: zoneName,
                    ancienne: ancienneMarge,
                    nouvelle: resultat.marge_utilisee
                });
            }
        }

        return suggestions;
    }

    /**
     * Applique les marges optimales à l'entité et la sauvegarde.
     */
    appliquerMargesOptimales() {
        const entiteNom = this.selectedEntite();
        if (entiteNom === 'none') return;

        this.entityService.getEntite(entiteNom).subscribe({
            next: (entite) => {
                const results = this.analyseResults();
                if (!results || !results.resultats || !entite.zones) return;

                let nbModifs = 0;
                for (const zone of entite.zones) {
                    const resultat = results.resultats[zone.nom];
                    if (resultat && resultat.marge_utilisee !== undefined) {
                        const ancienne = zone.margin || 0;
                        if (resultat.marge_utilisee !== ancienne) {
                            zone.margin = resultat.marge_utilisee;
                            nbModifs++;
                        }
                    }
                }

                if (nbModifs === 0) return;

                this.entityService.sauvegarderEntite(
                    entite.nom,
                    entite.zones,
                    entite.image_reference,
                    entite.description,
                    entite.cadre_reference
                ).subscribe({
                    next: () => {
                        this.errorMessage.set('');
                        alert(`✅ ${nbModifs} marge(s) mise(s) à jour dans "${entiteNom}". Le mode rapide utilisera ces valeurs.`);
                        // Recharger la liste des entités
                        this.entityService.listerEntites().subscribe(e => this.entites.set(e));
                    },
                    error: (err: any) => {
                        this.errorMessage.set('Erreur lors de la sauvegarde: ' + err.message);
                    }
                });
            }
        });
    }
}
