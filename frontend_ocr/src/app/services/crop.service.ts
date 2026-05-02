// crop.service.ts — Service Angular pour la découpe d'images
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface CropParams {
    x: number;
    y: number;
    width: number;
    height: number;
    format?: 'jpg' | 'png';
}

@Injectable({
    providedIn: 'root'
})
export class CropService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Découpe une seule image et retourne le blob résultant
     */
    cropImage(file: File, params: CropParams): Observable<Blob> {
        const formData = new FormData();
        formData.append('image', file);
        formData.append('x', params.x.toString());
        formData.append('y', params.y.toString());
        formData.append('width', params.width.toString());
        formData.append('height', params.height.toString());
        if (params.format) {
            formData.append('format', params.format);
        }
        return this.http.post(`${this.apiUrl}/crop-image`, formData, {
            responseType: 'blob'
        });
    }

    /**
     * Découpe un lot d'images avec les mêmes paramètres.
     * Retourne un ZIP contenant toutes les images découpées.
     */
    cropImageBatch(files: File[], params: CropParams): Observable<Blob> {
        const formData = new FormData();
        files.forEach(f => formData.append('images', f));
        formData.append('x', params.x.toString());
        formData.append('y', params.y.toString());
        formData.append('width', params.width.toString());
        formData.append('height', params.height.toString());
        if (params.format) {
            formData.append('format', params.format);
        }
        return this.http.post(`${this.apiUrl}/crop-image-batch`, formData, {
            responseType: 'blob'
        });
    }
}
