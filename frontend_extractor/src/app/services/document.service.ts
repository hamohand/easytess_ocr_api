// document.service.ts - Service Angular pour l'extraction et conversion de documents
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ExtractDocumentResponse, ConvertPdfResponse, ExtractTariffCodesResponse, NormalizeLabelsResponse } from './models';

interface ExtractionOptions {
    tableColumns?: number[];
    pages?: number[];
    strategy?: string;
}

@Injectable({
    providedIn: 'root'
})
export class DocumentService {
    private apiUrl = 'http://localhost:8083/api';

    constructor(private http: HttpClient) { }

    /** Construit un FormData avec le fichier et les options communes. */
    private buildFormData(file: File, options?: ExtractionOptions, extras?: Record<string, string>): FormData {
        const formData = new FormData();
        formData.append('file', file);

        if (options?.tableColumns) {
            formData.append('table_columns', JSON.stringify(options.tableColumns));
        }
        if (options?.pages) {
            formData.append('pages', JSON.stringify(options.pages));
        }
        if (options?.strategy) {
            formData.append('strategy', options.strategy);
        }
        if (extras) {
            Object.entries(extras).forEach(([key, value]) => formData.append(key, value));
        }

        return formData;
    }

    /**
     * Extraction unifiée — détecte automatiquement PDF ou DOCX
     */
    extractDocument(file: File, options?: ExtractionOptions): Observable<ExtractDocumentResponse> {
        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-document`, this.buildFormData(file, options)
        );
    }

    /**
     * Extraction PDF uniquement
     */
    extractPdf(file: File, options?: ExtractionOptions): Observable<ExtractDocumentResponse> {
        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-pdf`, this.buildFormData(file, options)
        );
    }

    /**
     * Extraction DOCX uniquement
     */
    extractDocx(file: File, options?: { tableColumns?: number[] }): Observable<ExtractDocumentResponse> {
        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-docx`, this.buildFormData(file, options)
        );
    }

    /**
     * Conversion PDF → DOCX (téléchargement direct du fichier)
     */
    convertPdfToDocx(file: File, options?: ExtractionOptions): Observable<Blob> {
        return this.http.post(`${this.apiUrl}/convert-pdf-to-docx`,
            this.buildFormData(file, options, { download: 'true' }),
            { responseType: 'blob' }
        );
    }

    /**
     * Conversion PDF → DOCX (retourne les stats, pas le fichier)
     */
    convertPdfToDocxInfo(file: File, options?: ExtractionOptions): Observable<ConvertPdfResponse> {
        return this.http.post<ConvertPdfResponse>(
            `${this.apiUrl}/convert-pdf-to-docx`,
            this.buildFormData(file, options, { download: 'false' })
        );
    }

    /**
     * Extraction dynamique des codes tarifaires (format XXXX.XX.XX.XX)
     */
    extractTariffCodes(file: File, options?: { pages?: number[]; strategy?: string }): Observable<ExtractTariffCodesResponse> {
        return this.http.post<ExtractTariffCodesResponse>(
            `${this.apiUrl}/extract-tariff-codes`, this.buildFormData(file, options)
        );
    }

    /**
     * Normalisation des étiquettes d'un tableau JSON d'objets
     */
    normalizeLabels(data: { [key: string]: any }[]): Observable<NormalizeLabelsResponse> {
        return this.http.post<NormalizeLabelsResponse>(
            `${this.apiUrl}/normalize-labels`, data
        );
    }
}

