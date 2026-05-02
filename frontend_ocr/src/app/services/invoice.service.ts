// invoice.service.ts — Service Angular pour l'extraction de factures
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { InvoiceExtractionResponse } from './models';

@Injectable({
    providedIn: 'root'
})
export class InvoiceService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Extrait les articles d'une facture (image ou PDF)
     */
    extraireFacture(file: File, lang: string = 'fra'): Observable<InvoiceExtractionResponse> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('lang', lang);
        return this.http.post<InvoiceExtractionResponse>(
            `${this.apiUrl}/extraire-facture`, formData
        );
    }

    /**
     * Extrait les articles de plusieurs factures
     */
    extraireFactureBatch(files: File[], lang: string = 'fra'): Observable<any> {
        const formData = new FormData();
        files.forEach(f => formData.append('files', f));
        formData.append('lang', lang);
        return this.http.post(`${this.apiUrl}/extraire-facture-batch`, formData);
    }

    /**
     * Télécharge les résultats en JSON
     */
    exporterJson(articles: any[], filename: string): Observable<Blob> {
        return this.http.post(
            `${this.apiUrl}/export-facture-json`,
            { articles, filename },
            { responseType: 'blob' }
        );
    }
}
