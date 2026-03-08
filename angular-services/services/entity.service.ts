// entity.service.ts - Service Angular pour la gestion des entités
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Entite, Zone, ImageEntiteUploadResponse } from './models';

@Injectable({
    providedIn: 'root'
})
export class EntityService {
    private apiUrl = 'http://localhost:8082/api';

    constructor(private http: HttpClient) { }

    /**
     * Liste toutes les entités disponibles
     */
    listerEntites(): Observable<Entite[]> {
        return this.http.get<Entite[]>(`${this.apiUrl}/entites`);
    }

    /**
     * Récupère une entité spécifique
     * @param nom - Nom de l'entité
     */
    getEntite(nom: string): Observable<Entite> {
        return this.http.get<Entite>(`${this.apiUrl}/entite/${nom}`);
    }

    /**
     * Définit une entité comme active (pour l'analyse)
     * @param nom - Nom de l'entité, ou 'none' pour désactiver
     */
    setEntiteActive(nom: string): Observable<{ success: boolean; active: string | null }> {
        return this.http.post<{ success: boolean; active: string | null }>(
            `${this.apiUrl}/set-entite-active/${nom}`,
            {}
        );
    }

    /**
     * Upload une image de référence pour une entité
     * @param file - Fichier image
     */
    uploadImageEntite(file: File): Observable<ImageEntiteUploadResponse> {
        const formData = new FormData();
        formData.append('image', file);
        return this.http.post<ImageEntiteUploadResponse>(`${this.apiUrl}/upload-image-entite`, formData);
    }

    /**
     * Sauvegarde une nouvelle entité (Angular-ready: envoie tout d'un coup)
     * @param nom - Nom de l'entité
     * @param zones - Liste des zones définies
     * @param imageFilename - Nom du fichier image uploadé
     * @param description - Description optionnelle
     */
    sauvegarderEntite(
        nom: string,
        zones: Zone[],
        imageFilename?: string,
        description?: string
    ): Observable<{ success: boolean }> {
        const body = {
            nom,
            zones,
            image_filename: imageFilename,
            description
        };
        return this.http.post<{ success: boolean }>(`${this.apiUrl}/sauvegarder-entite`, body);
    }

    /**
     * Modifie une zone existante dans une entité
     * @param nomEntite - Nom de l'entité
     * @param zoneId - ID de la zone
     * @param zone - Nouvelles données de la zone
     */
    modifierZone(nomEntite: string, zoneId: number, zone: Zone): Observable<{ success: boolean }> {
        return this.http.put<{ success: boolean }>(
            `${this.apiUrl}/entite/${nomEntite}/modifier-zone/${zoneId}`,
            zone
        );
    }

    /**
     * Supprime une zone d'une entité
     * @param nomEntite - Nom de l'entité
     * @param zoneId - ID de la zone
     */
    supprimerZone(nomEntite: string, zoneId: number): Observable<{ success: boolean }> {
        return this.http.delete<{ success: boolean }>(
            `${this.apiUrl}/entite/${nomEntite}/supprimer-zone/${zoneId}`
        );
    }
}
