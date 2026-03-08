// models.ts - Interfaces TypeScript pour l'API EasyTess

export interface Zone {
    id?: number;
    nom: string;
    coords: [number, number, number, number]; // [x1, y1, x2, y2]
    type?: 'text' | 'qrcode' | 'barcode';
    valeurs_attendues?: string[];
}

export interface Entite {
    nom: string;
    description?: string;
    date_creation?: string;
    image_reference?: string;
    zones: Zone[];
    metadata?: {
        nombre_zones: number;
        image_dimensions?: {
            width: number;
            height: number;
        };
    };
}

export interface ResultatOCR {
    texte_auto: string;
    confiance_auto: number;
    statut: 'ok' | 'faible_confiance' | 'echec' | 'corrigé';
    moteur: 'tesseract' | 'easyocr' | 'aucun';
    ameliore_par?: string;
    texte_final?: string;
    texte_corrige_manuel?: string;
}

export interface AnalyseResponse {
    success: boolean;
    resultats: { [zoneName: string]: ResultatOCR };
    alertes: string[];
    stats_moteurs: { [moteur: string]: number };
}

export interface UploadResponse {
    success: boolean;
    filename: string;
    saved_filename: string;
    url: string;
}

export interface ImageEntiteUploadResponse {
    success: boolean;
    filepath: string;
    filename: string;
    image_url: string;
    dimensions: {
        width: number;
        height: number;
    };
}
