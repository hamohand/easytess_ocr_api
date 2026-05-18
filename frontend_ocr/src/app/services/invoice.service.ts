// invoice.service.ts — Service Angular pour l'extraction de factures
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { InvoiceExtractionResponse } from './models';

export interface InvoiceDetectionResponse {
    success: boolean;
    zone?: { x_min: number; y_min: number; x_max: number; y_max: number };
    image_dimensions?: { width: number; height: number };
    preview_image_base64?: string;
    error?: string;
}

export interface ZoneManuelle {
    x_min: number;
    x_max: number;
    y_min: number;
    y_max: number;
}

@Injectable({
    providedIn: 'root'
})
export class InvoiceService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Détecte la zone des articles
     */
    detecterZone(file: File, lang: string = 'fra'): Observable<InvoiceDetectionResponse> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('lang', lang);
        return this.http.post<InvoiceDetectionResponse>(
            `${this.apiUrl}/detecter-zone`, formData
        );
    }

    /**
     * Extrait les articles d'une facture (image ou PDF)
     */
    extraireFacture(file: File, lang: string = 'fra', zoneManuelle?: ZoneManuelle): Observable<InvoiceExtractionResponse> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('lang', lang);
        if (zoneManuelle) {
            formData.append('zone_manuelle', JSON.stringify(zoneManuelle));
        }
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
