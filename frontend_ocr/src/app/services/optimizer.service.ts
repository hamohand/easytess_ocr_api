import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface OptimizerRequest {
    entity_name: string;
    zone_name: string;
    texte_attendu: string;
    use_tesseract?: boolean;
    use_easyocr?: boolean;
    stop_threshold?: number;
}

export interface OptimizerResult {
    zone: string;
    texte_attendu: string;
    duree_secondes?: number;
    initial: {
        coords: number[];
        texte: string;
        confiance: number;
        similarite: number;
        score: number;
    };
    optimal: {
        coords: number[];
        texte: string;
        confiance: number;
        similarite: number;
        score: number;
    };
    amelioration: number;
    nb_evaluations: number;
    error?: string;
}

@Injectable({
    providedIn: 'root'
})
export class OptimizerService {
    private apiUrl = 'http://localhost:8082/api/optimizer';

    constructor(private http: HttpClient) { }

    /**
     * Run zone optimization process
     * @param request Optimizer configuration parameters
     */
    runOptimization(request: OptimizerRequest): Observable<OptimizerResult> {
        return this.http.post<OptimizerResult>(`${this.apiUrl}/run`, request);
    }
}
