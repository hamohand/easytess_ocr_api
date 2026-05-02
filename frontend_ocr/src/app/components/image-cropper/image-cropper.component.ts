// image-cropper.component.ts — Composant de découpe d'images
import { Component, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CropService, CropParams } from '../../services/crop.service';

type CropMode = 'single' | 'folder';
type CropState = 'idle' | 'processing' | 'done' | 'error';

interface CropResult {
    filename: string;
    blobUrl: string;
    blob: Blob;
}

interface BatchResult {
    total: number;
    blobUrl: string;
    blob: Blob;
    filename: string;
}

@Component({
    selector: 'app-image-cropper',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './image-cropper.component.html',
    styleUrls: ['./image-cropper.component.css']
})
export class ImageCropperComponent {
    @ViewChild('fileInput') fileInput!: ElementRef<HTMLInputElement>;
    @ViewChild('folderInput') folderInput!: ElementRef<HTMLInputElement>;
    @ViewChild('previewImg') previewImg!: ElementRef<HTMLImageElement>;

    // Mode
    activeMode = signal<CropMode>('single');

    // State
    state = signal<CropState>('idle');
    isDragOver = signal<boolean>(false);
    errorMessage = signal<string | null>(null);

    // Crop params
    cropX = signal<number>(0);
    cropY = signal<number>(0);
    cropW = signal<number>(200);
    cropH = signal<number>(200);
    outputFormat = signal<'jpg' | 'png'>('jpg');

    // Single mode
    selectedFile = signal<File | null>(null);
    previewUrl = signal<string | null>(null);
    cropResult = signal<CropResult | null>(null);
    imageDimensions = signal<{ width: number; height: number } | null>(null);

    // Folder mode
    selectedFiles = signal<File[]>([]);
    batchResult = signal<BatchResult | null>(null);
    batchProgress = signal<number>(0);

    // Computed
    hasFile = computed(() => this.selectedFile() !== null);
    hasFiles = computed(() => this.selectedFiles().length > 0);
    fileInfo = computed(() => {
        const f = this.selectedFile();
        if (!f) return null;
        const sizeMB = (f.size / (1024 * 1024)).toFixed(2);
        const ext = f.name.split('.').pop()?.toUpperCase() || '';
        return { name: f.name, size: sizeMB, ext };
    });
    folderInfo = computed(() => {
        const files = this.selectedFiles();
        if (!files.length) return null;
        const totalSize = files.reduce((s, f) => s + f.size, 0);
        const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
        return { count: files.length, size: sizeMB };
    });
    cropParams = computed<CropParams>(() => ({
        x: this.cropX(),
        y: this.cropY(),
        width: this.cropW(),
        height: this.cropH(),
        format: this.outputFormat()
    }));

    // Validation
    paramsValid = computed(() => {
        return this.cropW() > 0 && this.cropH() > 0 && this.cropX() >= 0 && this.cropY() >= 0;
    });
    paramsWarning = computed(() => {
        const dims = this.imageDimensions();
        if (!dims) return null;
        const x = this.cropX(), y = this.cropY(), w = this.cropW(), h = this.cropH();
        if (x + w > dims.width || y + h > dims.height) {
            return `Le cadre dépasse l'image (${dims.width}×${dims.height}). Il sera tronqué automatiquement.`;
        }
        return null;
    });

    constructor(private cropService: CropService) {}

    // ─── Mode Switch ──────────────────────────────────────

    setMode(mode: CropMode) {
        this.activeMode.set(mode);
        this.clearAll();
    }

    // ─── Drag & Drop ──────────────────────────────────────

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
        if (!files || files.length === 0) return;

        if (this.activeMode() === 'single') {
            this.handleSingleFile(files[0]);
        } else {
            this.handleMultipleFiles(Array.from(files));
        }
    }

    // ─── File Selection ───────────────────────────────────

    onFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            this.handleSingleFile(input.files[0]);
        }
    }

    onFolderSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            this.handleMultipleFiles(Array.from(input.files));
        }
    }

    handleSingleFile(file: File) {
        if (!this.isImageFile(file)) {
            this.errorMessage.set(`Format non supporté: ${file.name}`);
            this.state.set('error');
            return;
        }

        this.selectedFile.set(file);
        this.errorMessage.set(null);
        this.cropResult.set(null);
        this.state.set('idle');

        // Preview + read dimensions
        const reader = new FileReader();
        reader.onload = (e) => {
            const dataUrl = e.target?.result as string;
            this.previewUrl.set(dataUrl);

            // Get dimensions
            const img = new Image();
            img.onload = () => {
                this.imageDimensions.set({ width: img.width, height: img.height });
            };
            img.src = dataUrl;
        };
        reader.readAsDataURL(file);
    }

    handleMultipleFiles(files: File[]) {
        const imageFiles = files.filter(f => this.isImageFile(f));
        if (imageFiles.length === 0) {
            this.errorMessage.set('Aucune image valide trouvée.');
            this.state.set('error');
            return;
        }
        this.selectedFiles.set(imageFiles);
        this.errorMessage.set(null);
        this.batchResult.set(null);
        this.state.set('idle');

        // Read dimensions of first image for reference
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                this.imageDimensions.set({ width: img.width, height: img.height });
            };
            img.src = e.target?.result as string;
        };
        reader.readAsDataURL(imageFiles[0]);
    }

    isImageFile(file: File): boolean {
        const exts = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'webp'];
        const ext = file.name.split('.').pop()?.toLowerCase() || '';
        return exts.includes(ext);
    }

    // ─── Clear ────────────────────────────────────────────

    clearAll() {
        // Revoke object URLs to prevent memory leaks
        const cr = this.cropResult();
        if (cr) URL.revokeObjectURL(cr.blobUrl);
        const br = this.batchResult();
        if (br) URL.revokeObjectURL(br.blobUrl);

        this.selectedFile.set(null);
        this.selectedFiles.set([]);
        this.previewUrl.set(null);
        this.cropResult.set(null);
        this.batchResult.set(null);
        this.errorMessage.set(null);
        this.imageDimensions.set(null);
        this.state.set('idle');
        this.batchProgress.set(0);

        if (this.fileInput?.nativeElement) this.fileInput.nativeElement.value = '';
        if (this.folderInput?.nativeElement) this.folderInput.nativeElement.value = '';
    }

    // ─── Crop Actions ─────────────────────────────────────

    lancerCrop() {
        if (this.activeMode() === 'single') {
            this.cropSingle();
        } else {
            this.cropBatch();
        }
    }

    private cropSingle() {
        const file = this.selectedFile();
        if (!file || !this.paramsValid()) return;

        this.state.set('processing');
        this.errorMessage.set(null);

        this.cropService.cropImage(file, this.cropParams()).subscribe({
            next: (blob) => {
                const ext = this.outputFormat();
                const baseName = file.name.replace(/\.[^.]+$/, '');
                const outputName = `${baseName}_crop.${ext}`;
                const blobUrl = URL.createObjectURL(blob);
                this.cropResult.set({ filename: outputName, blobUrl, blob });
                this.state.set('done');
            },
            error: (err) => {
                this.state.set('error');
                this.errorMessage.set(
                    err.error?.error || err.message || 'Erreur lors du rognage.'
                );
            }
        });
    }

    private cropBatch() {
        const files = this.selectedFiles();
        if (!files.length || !this.paramsValid()) return;

        this.state.set('processing');
        this.errorMessage.set(null);
        this.batchProgress.set(0);

        this.cropService.cropImageBatch(files, this.cropParams()).subscribe({
            next: (blob) => {
                const filename = `crop_batch_${new Date().toISOString().slice(0, 10)}.zip`;
                const blobUrl = URL.createObjectURL(blob);
                this.batchResult.set({ total: files.length, blobUrl, blob, filename });
                this.state.set('done');
            },
            error: (err) => {
                this.state.set('error');
                this.errorMessage.set(
                    err.error?.error || err.message || 'Erreur lors du rognage batch.'
                );
            }
        });
    }

    // ─── Download ─────────────────────────────────────────

    downloadResult() {
        const cr = this.cropResult();
        if (cr) {
            this.triggerDownload(cr.blobUrl, cr.filename);
        }
    }

    downloadBatchResult() {
        const br = this.batchResult();
        if (br) {
            this.triggerDownload(br.blobUrl, br.filename);
        }
    }

    private triggerDownload(url: string, filename: string) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
    }

    // ─── Helpers ──────────────────────────────────────────

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
            height: `${Math.max(h, 0)}px`
        };
    }
}
