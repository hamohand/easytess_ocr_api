// document-extractor.component.ts
import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DocumentService } from '../services/document.service';
import { DocumentBloc, ExtractDocumentResponse, ExtractionStats } from '../services/models';

type ExtractionMode = 'unified' | 'pdf' | 'convert' | 'position' | 'etiquettes' | 'hscode' | 'hscode10' | 'hscode10folder';
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
    activeTab = signal<'extraction' | 'code'>('extraction');
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

    // Folder mode
    selectedFolder = signal<File[]>([]);
    folderProgress = signal<string>('');

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
            case 'position': return '.pdf';
            case 'etiquettes': return '.pdf';
            case 'hscode': return '.pdf';
            case 'hscode10': return '.pdf';
            case 'convert': return '.pdf';
            case 'unified': return '.pdf,.docx';
            default: return '.pdf';
        }
    });

    constructor(private documentService: DocumentService) { }

    // ─── Tab switching ───
    setTab(tab: 'extraction' | 'code') {
        const previousTab = this.activeTab();
        this.activeTab.set(tab);

        if (tab === 'extraction') {
            this.setMode('unified', previousTab !== tab);
        } else {
            this.setMode('position', previousTab !== tab);
        }
    }

    // ─── Mode switching ───
    setMode(mode: ExtractionMode, forceReset: boolean = true) {
        // If we are just switching between position and etiquettes, we might want to keep the results
        // so that we can normalize the existing data.
        const codeTabModes: ExtractionMode[] = ['position', 'etiquettes', 'hscode', 'hscode10', 'hscode10folder'];
        const isCodeTabSwitch =
            codeTabModes.includes(this.activeMode()) && codeTabModes.includes(mode);
            
        this.activeMode.set(mode);
        
        if (forceReset && !isCodeTabSwitch) {
            this.resetResults();
        }
        // Reset file if format doesn't match
        const file = this.selectedFile();
        if (file) {
            const ext = file.name.split('.').pop()?.toLowerCase();
            if ((mode === 'pdf' || mode === 'convert' || mode === 'position' || mode === 'etiquettes' || mode === 'hscode' || mode === 'hscode10') && ext !== 'pdf') {
                this.selectedFile.set(null);
            }
        }
        if (mode !== 'hscode10folder') {
            this.selectedFolder.set([]);
            this.folderProgress.set('');
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
        
        if (mode === 'position') {
            this.documentService.extractTariffCodes(file, options).subscribe({
                next: (res: any) => {
                    const bloc: DocumentBloc = {
                        type: 'tableau',
                        numero: 1,
                        lignes: res.donnees,
                        metadata: {
                            nb_lignes: res.nb_lignes_trouvees,
                            nb_colonnes: res.donnees.length > 0 ? Object.keys(res.donnees[0]).length : 0,
                            a_entete: true
                        }
                    };
                    this.extractedContent.set([bloc]);
                    this.stats.set(null);
                    this.resultFilename.set(res.filename || file.name);
                    this.resultFormat.set('JSON');
                    this.loading.set(false);
                    this.expandedTables.set(new Set([0])); // Auto expand result
                },
                error: (err: any) => {
                    this.error.set(err.error?.error || 'Erreur lors de l\'extraction');
                    this.loading.set(false);
                }
            });
            return;
        }

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
            error: (err: any) => {
                this.error.set(err.error?.error || 'Erreur lors de l\'extraction');
                this.loading.set(false);
            }
        });
    }

    // ─── Normalize Labels ───
    normalizeLabels() {
        if (this.activeMode() !== 'etiquettes' || !this.hasResults()) return;

        this.loading.set(true);
        this.error.set(null);

        // Récupérer toutes les lignes actuelles des tableaux
        const currentData: any[] = [];
        const contentBlocks = this.extractedContent();
        
        contentBlocks.forEach(block => {
            if (block.type === 'tableau' && block.lignes) {
                currentData.push(...block.lignes);
            }
        });

        if (currentData.length === 0) {
            this.error.set('Aucune ligne de tableau à normaliser.');
            this.loading.set(false);
            return;
        }

        this.documentService.normalizeLabels(currentData).subscribe({
            next: (res: any) => {
                // Remplacer le contenu affiché par le résultat normalisé dans un unique bloc tableau
                const bloc: DocumentBloc = {
                    type: 'tableau',
                    numero: 1,
                    lignes: res.donnees,
                    metadata: {
                        nb_lignes: res.nb_lignes_normalisees,
                        nb_colonnes: res.donnees.length > 0 ? Object.keys(res.donnees[0]).length : 0,
                        a_entete: true
                    }
                };
                this.extractedContent.set([bloc]);
                this.loading.set(false);
                this.expandedTables.set(new Set([0]));
            },
            error: (err: any) => {
                this.error.set(err.error?.error || 'Erreur lors de la normalisation');
                this.loading.set(false);
            }
        });
    }

    // ─── Generate Hscode JSON ───
    private findKey(row: any, hint: string): string {
        const lower = hint.toLowerCase();
        const key = Object.keys(row).find(k => k.toLowerCase().includes(lower));
        return key ? (row[key] || '') : '';
    }

    generateHscode() {
        const content = this.extractedContent();
        if (!content.length) return;

        const rows: any[] = [];
        content.forEach(bloc => {
            if (bloc.type === 'tableau' && bloc.lignes) {
                rows.push(...bloc.lignes);
            }
        });

        const hscodeData = rows
            .map(row => ({
                code: this.findKey(row, 'position').replace(/[^0-9]/g, ''),
                description: this.findKey(row, 'désignation') || this.findKey(row, 'designation')
            }))
            .filter(item => item.code || item.description)
            .sort((a, b) => a.code.localeCompare(b.code, undefined, { numeric: true }));

        const blob = new Blob([JSON.stringify(hscodeData, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'hscode.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    // ─── Hscode10 : pipeline complet PDF → hscode.json ───
    generateHscode10() {
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

        // Étape 1 : extraction des codes tarifaires
        this.documentService.extractTariffCodes(file, options).subscribe({
            next: (res: any) => {
                const rows: any[] = res.donnees || [];
                if (rows.length === 0) {
                    this.error.set('Aucune ligne trouvée lors de l\'extraction.');
                    this.loading.set(false);
                    return;
                }

                // Étape 2 : normalisation des étiquettes
                this.documentService.normalizeLabels(rows).subscribe({
                    next: (norm: any) => {
                        const normalizedRows: any[] = norm.donnees || [];

                        // Étape 3 : génération de hscode.json
                        const hscodeData = normalizedRows
                            .map(row => ({
                                code: this.findKey(row, 'position').replace(/[^0-9]/g, ''),
                                description: this.findKey(row, 'désignation') || this.findKey(row, 'designation')
                            }))
                            .filter(item => item.code || item.description);

                        const blob = new Blob([JSON.stringify(hscodeData, null, 2)], { type: 'application/json' });
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'hscode.json';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);

                        this.loading.set(false);
                    },
                    error: (err: any) => {
                        this.error.set(err.error?.error || 'Erreur lors de la normalisation');
                        this.loading.set(false);
                    }
                });
            },
            error: (err: any) => {
                this.error.set(err.error?.error || 'Erreur lors de l\'extraction des codes');
                this.loading.set(false);
            }
        });
    }

    // ─── Hscode10-dossier : sélection dossier ───
    onFolderSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files) return;
        const pdfs = Array.from(input.files)
            .filter(f => f.name.toLowerCase().endsWith('.pdf'))
            .sort((a, b) => this.getRelativePath(a).localeCompare(this.getRelativePath(b)));
        this.selectedFolder.set(pdfs);
        this.folderProgress.set('');
        this.error.set(null);
    }

    getRelativePath(file: File): string {
        return (file as any).webkitRelativePath || file.name;
    }

    removeFolder() {
        this.selectedFolder.set([]);
        this.folderProgress.set('');
        this.error.set(null);
    }

    // ─── Hscode10-dossier : pipeline complet dossier → hscode.json ───
    async generateHscode10Folder() {
        const files = this.selectedFolder();
        if (!files.length) return;

        this.loading.set(true);
        this.error.set(null);
        this.folderProgress.set('');

        const options = { strategy: this.strategy() };
        const allRows: any[] = [];

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            this.folderProgress.set(`Traitement ${i + 1} / ${files.length} : ${this.getRelativePath(file)}`);

            try {
                // Étape 1 : extraction des codes tarifaires
                const res: any = await this.documentService.extractTariffCodes(file, options).toPromise();
                const rows: any[] = res?.donnees || [];
                if (!rows.length) continue;

                // Étape 2 : normalisation
                const norm: any = await this.documentService.normalizeLabels(rows).toPromise();
                allRows.push(...(norm?.donnees || []));
            } catch (err: any) {
                this.error.set(`Erreur sur "${file.name}": ${err?.error?.error || err?.message || 'Erreur inconnue'}`);
                this.loading.set(false);
                this.folderProgress.set('');
                return;
            }
        }

        this.folderProgress.set(`${files.length} fichier(s) traité(s) — ${allRows.length} lignes collectées.`);

        // Étape 3 : génération du JSON
        const hscodeData = allRows
            .map(row => ({
                code: this.findKey(row, 'position').replace(/[^0-9]/g, ''),
                description: this.findKey(row, 'désignation') || this.findKey(row, 'designation')
            }))
            .filter(item => item.code || item.description);

        const blob = new Blob([JSON.stringify(hscodeData, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'hscode.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        this.loading.set(false);
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
