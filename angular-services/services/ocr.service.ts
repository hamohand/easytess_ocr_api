// ocr.service.ts - Service Angular pour les opérations OCR
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalyseResponse, ResultatOCR } from './models';

@Injectable({
    providedIn: 'root'
})
export class OcrService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Analyse une image avec OCR
     * @param filename - Nom du fichier uploadé (retourné par uploadImage)
     * @param zones - (Optionnel) Configuration des zones à analyser
     */
    analyserImage(filename: string, zones?: any): Observable<AnalyseResponse> {
        const body = { filename, zones };
        return this.http.post<AnalyseResponse>(`${this.apiUrl}/analyser`, body);
    }

    /**
     * Récupère les résultats stockés en session
     */
    getResultats(): Observable<{ [zoneName: string]: ResultatOCR }> {
        return this.http.get<{ [zoneName: string]: ResultatOCR }>(`${this.apiUrl}/resultats`);
    }

    /**
     * Sauvegarde les corrections manuelles
     * @param corrections - Objet avec les corrections { zoneName: texteCorrigé }
     */
    sauvegarderCorrections(corrections: { [key: string]: string }): Observable<{ success: boolean }> {
        return this.http.post<{ success: boolean }>(`${this.apiUrl}/resultats`, corrections);
    }

    /**
     * Récupère les zones nécessitant une correction
     */
    getCorrections(): Observable<{ [zoneName: string]: ResultatOCR }> {
        return this.http.get<{ [zoneName: string]: ResultatOCR }>(`${this.apiUrl}/corrections`);
    }
}
