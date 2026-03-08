// document.service.ts - Service Angular pour l'extraction et conversion de documents
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ExtractDocumentResponse, ConvertPdfResponse } from './models';

@Injectable({
    providedIn: 'root'
})
export class DocumentService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Extraction unifiée — détecte automatiquement PDF ou DOCX
     */
    extractDocument(file: File, options?: {
        tableColumns?: number[];
        pages?: number[];
        strategy?: string;
    }): Observable<ExtractDocumentResponse> {
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

        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-document`, formData
        );
    }

    /**
     * Extraction PDF uniquement
     */
    extractPdf(file: File, options?: {
        tableColumns?: number[];
        pages?: number[];
        strategy?: string;
    }): Observable<ExtractDocumentResponse> {
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

        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-pdf`, formData
        );
    }

    /**
     * Extraction DOCX uniquement
     */
    extractDocx(file: File, options?: {
        tableColumns?: number[];
    }): Observable<ExtractDocumentResponse> {
        const formData = new FormData();
        formData.append('file', file);

        if (options?.tableColumns) {
            formData.append('table_columns', JSON.stringify(options.tableColumns));
        }

        return this.http.post<ExtractDocumentResponse>(
            `${this.apiUrl}/extract-docx`, formData
        );
    }

    /**
     * Conversion PDF → DOCX (téléchargement direct du fichier)
     */
    convertPdfToDocx(file: File, options?: {
        tableColumns?: number[];
        pages?: number[];
        strategy?: string;
    }): Observable<Blob> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('download', 'true');

        if (options?.tableColumns) {
            formData.append('table_columns', JSON.stringify(options.tableColumns));
        }
        if (options?.pages) {
            formData.append('pages', JSON.stringify(options.pages));
        }
        if (options?.strategy) {
            formData.append('strategy', options.strategy);
        }

        return this.http.post(`${this.apiUrl}/convert-pdf-to-docx`, formData, {
            responseType: 'blob'
        });
    }

    /**
     * Conversion PDF → DOCX (retourne les stats, pas le fichier)
     */
    convertPdfToDocxInfo(file: File, options?: {
        tableColumns?: number[];
        pages?: number[];
        strategy?: string;
    }): Observable<ConvertPdfResponse> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('download', 'false');

        if (options?.tableColumns) {
            formData.append('table_columns', JSON.stringify(options.tableColumns));
        }
        if (options?.pages) {
            formData.append('pages', JSON.stringify(options.pages));
        }
        if (options?.strategy) {
            formData.append('strategy', options.strategy);
        }

        return this.http.post<ConvertPdfResponse>(
            `${this.apiUrl}/convert-pdf-to-docx`, formData
        );
    }
}
