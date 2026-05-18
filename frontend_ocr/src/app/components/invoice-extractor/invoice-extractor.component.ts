// invoice-extractor.component.ts — Composant d'extraction de factures
import { Component, signal, computed, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InvoiceService } from '../../services/invoice.service';
import { InvoiceArticle, InvoiceExtractionResponse } from '../../services/models';

type ExtractionState = 'idle' | 'uploading' | 'detecting' | 'validating_zone' | 'processing' | 'results' | 'error';

@Component({
    selector: 'app-invoice-extractor',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './invoice-extractor.component.html',
    styleUrls: ['./invoice-extractor.component.css']
})
export class InvoiceExtractorComponent {
    @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
    @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

    // State
    state = signal<ExtractionState>('idle');
    selectedFile = signal<File | null>(null);
    previewUrl = signal<string | null>(null);
    isDragOver = signal<boolean>(false);
    lang = signal<string>('fra');

    // Zone params
    cropX = signal<number>(0);
    cropY = signal<number>(0);
    cropW = signal<number>(0);
    cropH = signal<number>(0);
    imageDimensions = signal<{ width: number; height: number } | null>(null);

    // Results
    articles = signal<InvoiceArticle[]>([]);
    response = signal<InvoiceExtractionResponse | null>(null);
    errorMessage = signal<string | null>(null);

    // Computed
    hasResults = computed(() => this.articles().length > 0);
    fileInfo = computed(() => {
        const f = this.selectedFile();
        if (!f) return null;
        const sizeMB = (f.size / (1024 * 1024)).toFixed(2);
        const ext = f.name.split('.').pop()?.toUpperCase() || '';
        return { name: f.name, size: sizeMB, ext };
    });

    constructor(private invoiceService: InvoiceService) {}

    // ─── File Handling ────────────────────────────────────

    onDragOver(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver.set(true);
    }

    onDragLeave(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver.set(false);
    }

    onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.isDragOver.set(false);

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            this.handleFile(files[0]);
        }
    }

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            this.handleFile(input.files[0]);
        }
    }

    handleFile(file: File) {
        // Validate extension
        const allowedExts = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp', 'pdf'];
        const ext = file.name.split('.').pop()?.toLowerCase() || '';
        if (!allowedExts.includes(ext)) {
            this.errorMessage.set(`Format non supporté: .${ext}`);
            this.state.set('error');
            return;
        }

        this.selectedFile.set(file);
        this.errorMessage.set(null);
        this.articles.set([]);
        this.response.set(null);
        this.state.set('idle');

        // Preview
        if (ext !== 'pdf') {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.previewUrl.set(e.target?.result as string);
                const img = new Image();
                img.onload = () => {
                    this.imageDimensions.set({ width: img.width, height: img.height });
                    this.cropX.set(0);
                    this.cropY.set(0);
                    this.cropW.set(img.width);
                    this.cropH.set(img.height);
                };
                img.src = e.target?.result as string;
            };
            reader.readAsDataURL(file);
        } else {
            this.previewUrl.set(null);
            this.imageDimensions.set(null);
        }
    }

    clearFile() {
        this.selectedFile.set(null);
        this.previewUrl.set(null);
        this.articles.set([]);
        this.response.set(null);
        this.errorMessage.set(null);
        this.state.set('idle');
        this.imageDimensions.set(null);
        if (this.fileInput) {
            this.fileInput.nativeElement.value = '';
        }
    }

    // ─── Extraction ───────────────────────────────────────

    lancerDetection() {
        const file = this.selectedFile();
        if (!file) return;

        this.state.set('detecting');
        this.errorMessage.set(null);

        this.invoiceService.detecterZone(file, this.lang()).subscribe({
            next: (res) => {
                if (res.success && res.zone) {
                    if (res.preview_image_base64) {
                        this.previewUrl.set(res.preview_image_base64);
                        // Force update of dimensions if image dimensions are returned
                        if (res.image_dimensions) {
                            this.imageDimensions.set(res.image_dimensions);
                        }
                    }
                    
                    const dims = res.image_dimensions;
                    if (dims) {
                        this.imageDimensions.set(dims);
                        this.cropX.set(Math.floor(res.zone.x_min * dims.width));
                        this.cropY.set(Math.floor(res.zone.y_min * dims.height));
                        this.cropW.set(Math.ceil((res.zone.x_max - res.zone.x_min) * dims.width));
                        this.cropH.set(Math.ceil((res.zone.y_max - res.zone.y_min) * dims.height));
                    }
                    this.state.set('validating_zone');
                } else {
                    this.state.set('error');
                    this.errorMessage.set(res.error || 'Erreur lors de la détection de la zone.');
                }
            },
            error: (err) => {
                this.state.set('error');
                this.errorMessage.set(err.error?.error || err.message || 'Erreur de communication avec le serveur.');
            }
        });
    }

    lancerExtraction() {
        const file = this.selectedFile();
        if (!file) return;

        this.state.set('processing');
        this.errorMessage.set(null);

        let zoneManuelle = undefined;
        const dims = this.imageDimensions();
        // Si on est en train de valider une zone d'une image, on la passe
        if (dims && this.state() !== 'idle') {
            zoneManuelle = {
                x_min: this.cropX() / dims.width,
                x_max: (this.cropX() + this.cropW()) / dims.width,
                y_min: this.cropY() / dims.height,
                y_max: (this.cropY() + this.cropH()) / dims.height,
            };
        }

        this.invoiceService.extraireFacture(file, this.lang(), zoneManuelle).subscribe({
            next: (res) => {
                this.response.set(res);
                this.articles.set(res.articles || []);

                if (res.success && res.nb_articles > 0) {
                    this.state.set('results');
                } else {
                    this.state.set('error');
                    this.errorMessage.set(
                        res.error || 'Aucun article trouvé dans la facture.'
                    );
                }
            },
            error: (err) => {
                this.state.set('error');
                this.errorMessage.set(
                    err.error?.error || err.message || 'Erreur de communication avec le serveur.'
                );
            }
        });
    }

    // ─── Export ────────────────────────────────────────────

    exporterJson() {
        const arts = this.articles();
        const file = this.selectedFile();
        if (!arts.length) return;

        this.invoiceService.exporterJson(arts, file?.name || 'facture').subscribe({
            next: (blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `articles_${file?.name || 'facture'}.json`;
                a.click();
                window.URL.revokeObjectURL(url);
            },
            error: (err) => {
                console.error('Export error:', err);
            }
        });
    }

    exporterCsv() {
        const arts = this.articles();
        if (!arts.length) return;

        // Build CSV
        const headers = ['N°', 'Désignation', 'Confiance (%)'];
        const rows = arts.map((a, i) => [
            i + 1,
            `"${a.designation.replace(/"/g, '""')}"`,
            a.confiance
        ]);

        const csv = [headers.join(';'), ...rows.map(r => r.join(';'))].join('\n');
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `articles_${this.selectedFile()?.name || 'facture'}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    }

    // ─── Article Editing ──────────────────────────────────

    supprimerArticle(index: number) {
        const current = [...this.articles()];
        current.splice(index, 1);
        this.articles.set(current);
    }

    updateArticle(index: number, newValue: string) {
        const current = [...this.articles()];
        current[index] = { ...current[index], designation: newValue };
        this.articles.set(current);
    }

    // ─── Zone interactions ────────────────────────────────
    
    @ViewChild('previewImg') previewImg!: ElementRef<HTMLImageElement>;

    updateCropParam(param: 'x' | 'y' | 'width' | 'height', event: Event) {
        const value = parseInt((event.target as HTMLInputElement).value, 10);
        if (isNaN(value)) return;
        switch (param) {
            case 'x': this.cropX.set(value); break;
            case 'y': this.cropY.set(value); break;
            case 'width': this.cropW.set(value); break;
            case 'height': this.cropH.set(value); break;
        }
    }

    getCropOverlayStyle(): Record<string, string> {
        const dims = this.imageDimensions();
        if (!dims || !this.previewImg?.nativeElement) return {};

        const imgEl = this.previewImg.nativeElement;
        const displayW = imgEl.clientWidth;
        const displayH = imgEl.clientHeight;
        if (displayW === 0 || displayH === 0) return {};

        const scaleX = displayW / dims.width;
        const scaleY = displayH / dims.height;

        const x = this.cropX() * scaleX;
        const y = this.cropY() * scaleY;
        const w = Math.min(this.cropW(), dims.width - this.cropX()) * scaleX;
        const h = Math.min(this.cropH(), dims.height - this.cropY()) * scaleY;

        return {
            left: `${x}px`,
            top: `${y}px`,
            width: `${Math.max(w, 0)}px`,
            height: `${Math.max(h, 0)}px`,
            position: 'absolute',
            border: '2.5px solid #10b981',
            background: 'rgba(16, 185, 129, 0.12)',
            borderRadius: '3px',
            boxShadow: '0 0 0 2000px rgba(0, 0, 0, 0.3)',
            cursor: 'move'
        };
    }

    // ─── Drag & Resize Logic ──────────────────────────────
    
    private dragMode: 'move' | 'nw' | 'ne' | 'sw' | 'se' | null = null;
    private dragStartX = 0;
    private dragStartY = 0;
    private dragStartCropX = 0;
    private dragStartCropY = 0;
    private dragStartCropW = 0;
    private dragStartCropH = 0;

    onOverlayMouseDown(event: MouseEvent) {
        if (this.state() !== 'validating_zone') return;
        event.preventDefault();
        event.stopPropagation();
        this.dragMode = 'move';
        this.startDrag(event);
    }

    onResizeMouseDown(event: MouseEvent, mode: 'nw' | 'ne' | 'sw' | 'se') {
        if (this.state() !== 'validating_zone') return;
        event.preventDefault();
        event.stopPropagation();
        this.dragMode = mode;
        this.startDrag(event);
    }

    private startDrag(event: MouseEvent) {
        this.dragStartX = event.clientX;
        this.dragStartY = event.clientY;
        this.dragStartCropX = this.cropX();
        this.dragStartCropY = this.cropY();
        this.dragStartCropW = this.cropW();
        this.dragStartCropH = this.cropH();
    }

    @HostListener('window:mousemove', ['$event'])
    onWindowMouseMove(event: MouseEvent) {
        if (!this.dragMode || !this.imageDimensions() || !this.previewImg?.nativeElement) return;
        
        event.preventDefault();

        const imgEl = this.previewImg.nativeElement;
        const displayW = imgEl.clientWidth;
        const displayH = imgEl.clientHeight;
        const dims = this.imageDimensions()!;
        
        const scaleX = dims.width / displayW;
        const scaleY = dims.height / displayH;

        const deltaX = (event.clientX - this.dragStartX) * scaleX;
        const deltaY = (event.clientY - this.dragStartY) * scaleY;

        let newX = this.dragStartCropX;
        let newY = this.dragStartCropY;
        let newW = this.dragStartCropW;
        let newH = this.dragStartCropH;

        if (this.dragMode === 'move') {
            newX += deltaX;
            newY += deltaY;
        } else if (this.dragMode === 'nw') {
            newX += deltaX;
            newY += deltaY;
            newW -= deltaX;
            newH -= deltaY;
        } else if (this.dragMode === 'ne') {
            newY += deltaY;
            newW += deltaX;
            newH -= deltaY;
        } else if (this.dragMode === 'sw') {
            newX += deltaX;
            newW -= deltaX;
            newH += deltaY;
        } else if (this.dragMode === 'se') {
            newW += deltaX;
            newH += deltaY;
        }

        // Constraints minimum width/height
        if (newW < 20) {
            if (this.dragMode === 'nw' || this.dragMode === 'sw') newX = this.dragStartCropX + this.dragStartCropW - 20;
            newW = 20;
        }
        if (newH < 20) {
            if (this.dragMode === 'nw' || this.dragMode === 'ne') newY = this.dragStartCropY + this.dragStartCropH - 20;
            newH = 20;
        }
        
        // Boundaries checks
        if (newX < 0) {
            if (this.dragMode !== 'move') newW += newX;
            newX = 0;
        }
        if (newY < 0) {
            if (this.dragMode !== 'move') newH += newY;
            newY = 0;
        }
        if (newX + newW > dims.width) {
            if (this.dragMode === 'move') newX = dims.width - newW;
            else newW = dims.width - newX;
        }
        if (newY + newH > dims.height) {
            if (this.dragMode === 'move') newY = dims.height - newH;
            else newH = dims.height - newY;
        }

        this.cropX.set(Math.round(newX));
        this.cropY.set(Math.round(newY));
        this.cropW.set(Math.round(newW));
        this.cropH.set(Math.round(newH));
    }

    @HostListener('window:mouseup', ['$event'])
    onWindowMouseUp(event: MouseEvent) {
        if (this.dragMode) {
            this.dragMode = null;
        }
    }
}
