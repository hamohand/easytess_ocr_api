// file.service.ts - Service Angular pour la gestion des fichiers
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { UploadResponse } from './models';

@Injectable({
    providedIn: 'root'
})
export class FileService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Upload une image pour l'analyse OCR
     * @param file - Fichier image
     */
    uploadImage(file: File): Observable<UploadResponse> {
        const formData = new FormData();
        formData.append('image', file);
        return this.http.post<UploadResponse>(`${this.apiUrl}/upload`, formData);
    }

    /**
     * Récupère l'URL d'une image uploadée
     * @param filename - Nom du fichier
     */
    getImageUrl(filename: string): string {
        return `http://localhost:8082/uploads/${filename}`;
    }

    /**
     * Exporte les résultats en JSON (retourne l'objet)
     */
    exportJson(): Observable<any> {
        return this.http.get(`${this.apiUrl}/export-json`);
    }

    /**
     * Télécharge les résultats en fichier JSON
     */
    downloadJsonFile(data?: any): Observable<Blob> {
        if (data) {
            return this.http.post(`${this.apiUrl}/export-json-file`, data, {
                responseType: 'blob'
            });
        }
        return this.http.get(`${this.apiUrl}/export-json-file`, {
            responseType: 'blob'
        });
    }
}
