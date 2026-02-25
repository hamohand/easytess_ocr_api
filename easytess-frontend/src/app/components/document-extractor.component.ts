// document-extractor.component.ts
import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DocumentService } from '../services/document.service';
import { DocumentBloc, ExtractDocumentResponse, ExtractionStats } from '../services/models';

type ExtractionMode = 'unified' | 'pdf' | 'convert';
type Strategy = 'auto' | 'standard' | 'text' | 'lines_strict';

@Component({
    selector: 'app-document-extractor',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './document-extractor.component.html',
    styleUrls: ['./document-extractor.component.css']
})
export class DocumentExtractorComponent {

    // ─── State ───
    activeMode = signal<ExtractionMode>('unified');
    selectedFile = signal<File | null>(null);
    dragOver = signal(false);

    // Options
    strategy = signal<Strategy>('auto');
    pagesFilter = signal<string>('');
    columnsFilter = signal<string>('');

    // Results
    loading = signal(false);
    error = signal<string | null>(null);
    extractedContent = signal<DocumentBloc[]>([]);
    stats = signal<ExtractionStats | null>(null);
    resultFilename = signal<string>('');
    resultFormat = signal<string>('');

    // Conversion
    converting = signal(false);
    convertSuccess = signal(false);

    // View
    expandedTables = signal<Set<number>>(new Set());
    showJsonPreview = signal(false);

    // Computed
    hasResults = computed(() => this.extractedContent().length > 0);
    textBlocs = computed(() => this.extractedContent().filter(b => b.type === 'texte'));
    tableBlocs = computed(() => this.extractedContent().filter(b => b.type === 'tableau'));

    fileInfo = computed(() => {
        const f = this.selectedFile();
        if (!f) return null;
        const ext = f.name.split('.').pop()?.toLowerCase() || '';
        const sizeMB = (f.size / 1024 / 1024).toFixed(2);
        return { name: f.name, ext, size: `${sizeMB} Mo`, isPdf: ext === 'pdf', isDocx: ext === 'docx' };
    });

    acceptedFormats = computed(() => {
        switch (this.activeMode()) {
            case 'pdf': return '.pdf';
            case 'convert': return '.pdf';
            case 'unified': return '.pdf,.docx';
        }
    });

    constructor(private documentService: DocumentService) { }

    // ─── Mode switching ───
    setMode(mode: ExtractionMode) {
        this.activeMode.set(mode);
        this.resetResults();
        // Reset file if format doesn't match
        const file = this.selectedFile();
        if (file) {
            const ext = file.name.split('.').pop()?.toLowerCase();
            if (mode === 'pdf' && ext !== 'pdf') this.selectedFile.set(null);
            if (mode === 'convert' && ext !== 'pdf') this.selectedFile.set(null);
        }
    }

    // ─── File handling ───
    onDragOver(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.dragOver.set(true);
    }

    onDragLeave(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.dragOver.set(false);
    }

    onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation();
        this.dragOver.set(false);

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
        const ext = file.name.split('.').pop()?.toLowerCase();
        const accepted = this.acceptedFormats().split(',').map(f => f.replace('.', ''));

        if (!accepted.includes(ext || '')) {
            this.error.set(`Format .${ext} non supporté. Formats acceptés: ${this.acceptedFormats()}`);
            return;
        }

        this.selectedFile.set(file);
        this.resetResults();
    }

    removeFile() {
        this.selectedFile.set(null);
        this.resetResults();
    }

    // ─── Options parsing ───
    private parsePages(): number[] | undefined {
        const raw = this.pagesFilter().trim();
        if (!raw) return undefined;
        try {
            // Accept "1,3,5" or "1-5"
            const pages: number[] = [];
            raw.split(',').forEach(part => {
                part = part.trim();
                if (part.includes('-')) {
                    const [start, end] = part.split('-').map(Number);
                    for (let i = start; i <= end; i++) pages.push(i);
                } else {
                    pages.push(Number(part));
                }
            });
            return pages.filter(p => !isNaN(p) && p > 0);
        } catch {
            return undefined;
        }
    }

    private parseColumns(): number[] | undefined {
        const raw = this.columnsFilter().trim();
        if (!raw) return undefined;
        try {
            return raw.split(',').map(c => Number(c.trim())).filter(c => !isNaN(c) && c >= 0);
        } catch {
            return undefined;
        }
    }

    // ─── Extract action ───
    extract() {
        const file = this.selectedFile();
        if (!file) return;

        this.loading.set(true);
        this.error.set(null);
        this.resetResults();

        const options = {
            tableColumns: this.parseColumns(),
            pages: this.parsePages(),
            strategy: this.strategy()
        };

        const mode = this.activeMode();
        let obs;

        if (mode === 'pdf') {
            obs = this.documentService.extractPdf(file, options);
        } else {
            obs = this.documentService.extractDocument(file, options);
        }

        obs.subscribe({
            next: (res: ExtractDocumentResponse) => {
                this.extractedContent.set(res.contenu || []);
                this.stats.set(res.statistiques || null);
                this.resultFilename.set(res.filename || file.name);
                this.resultFormat.set(res.format || '');
                this.loading.set(false);
            },
            error: (err) => {
                this.error.set(err.error?.error || 'Erreur lors de l\'extraction');
                this.loading.set(false);
            }
        });
    }

    // ─── Convert PDF → DOCX ───
    convertToDocx() {
        const file = this.selectedFile();
        if (!file) return;

        this.converting.set(true);
        this.convertSuccess.set(false);
        this.error.set(null);

        const options = {
            tableColumns: this.parseColumns(),
            pages: this.parsePages(),
            strategy: this.strategy()
        };

        this.documentService.convertPdfToDocx(file, options).subscribe({
            next: (blob: Blob) => {
                // Trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = file.name.replace(/\.pdf$/i, '.docx');
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.converting.set(false);
                this.convertSuccess.set(true);
                setTimeout(() => this.convertSuccess.set(false), 4000);
            },
            error: (err) => {
                this.error.set(err.error?.error || 'Erreur lors de la conversion');
                this.converting.set(false);
            }
        });
    }

    // ─── Export JSON ───
    exportJson() {
        const content = this.extractedContent();
        if (!content.length) return;

        const data = {
            filename: this.resultFilename(),
            format: this.resultFormat(),
            extraction_date: new Date().toISOString(),
            total_blocs: content.length,
            statistiques: this.stats(),
            contenu: content
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = this.resultFilename().replace(/\.[^.]+$/, '_extraction.json');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // ─── Table expansion ───
    toggleTable(index: number) {
        const expanded = new Set(this.expandedTables());
        if (expanded.has(index)) {
            expanded.delete(index);
        } else {
            expanded.add(index);
        }
        this.expandedTables.set(expanded);
    }

    isTableExpanded(index: number): boolean {
        return this.expandedTables().has(index);
    }

    // ─── JSON preview ───
    toggleJsonPreview() {
        this.showJsonPreview.update(v => !v);
    }

    getJsonPreview(): string {
        return JSON.stringify(this.extractedContent(), null, 2);
    }

    // ─── Helpers ───
    getTableKeys(bloc: DocumentBloc): string[] {
        if (!bloc.lignes || bloc.lignes.length === 0) return [];
        const keys: string[] = [];
        bloc.lignes.forEach(row => {
            Object.keys(row).forEach(k => {
                if (!keys.includes(k)) keys.push(k);
            });
        });
        return keys;
    }

    getFormatLabel(key: string): string {
        if (key.startsWith('col_')) {
            return `Col ${parseInt(key.replace('col_', '')) + 1}`;
        }
        return key;
    }

    resetResults() {
        this.extractedContent.set([]);
        this.stats.set(null);
        this.error.set(null);
        this.resultFilename.set('');
        this.resultFormat.set('');
        this.expandedTables.set(new Set());
        this.showJsonPreview.set(false);
    }
}
