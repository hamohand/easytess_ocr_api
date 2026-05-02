// invoice-extractor.component.ts — Composant d'extraction de factures
import { Component, signal, computed, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { InvoiceService } from '../../services/invoice.service';
import { InvoiceArticle, InvoiceExtractionResponse } from '../../services/models';

type ExtractionState = 'idle' | 'uploading' | 'processing' | 'results' | 'error';

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
            };
            reader.readAsDataURL(file);
        } else {
            this.previewUrl.set(null);
        }
    }

    clearFile() {
        this.selectedFile.set(null);
        this.previewUrl.set(null);
        this.articles.set([]);
        this.response.set(null);
        this.errorMessage.set(null);
        this.state.set('idle');
        if (this.fileInput) {
            this.fileInput.nativeElement.value = '';
        }
    }

    // ─── Extraction ───────────────────────────────────────

    lancerExtraction() {
        const file = this.selectedFile();
        if (!file) return;

        this.state.set('processing');
        this.errorMessage.set(null);

        this.invoiceService.extraireFacture(file, this.lang()).subscribe({
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
}
