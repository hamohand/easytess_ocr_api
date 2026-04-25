// models.ts - Interfaces TypeScript pour l'API Extraction de Documents

// ─── Document extraction models ───────────────────────────

export interface DocumentBloc {
    type: 'texte' | 'tableau';
    contenu?: string;           // Pour type 'texte'
    page?: number;
    numero?: number;            // Pour type 'tableau'
    lignes?: { [key: string]: string }[];
    metadata?: TableMetadata;
}

export interface TableMetadata {
    nb_lignes: number;
    nb_colonnes: number;
    a_entete: boolean;
    entetes?: string[];
    bbox?: { x0: number; y0: number; x1: number; y1: number };
}

export interface PageStats {
    page: number;
    nb_textes: number;
    nb_tableaux: number;
}

export interface ExtractionStats {
    total_pages: number;
    pages_traitees: number;
    total_blocs: number;
    nb_textes: number;
    nb_tableaux: number;
    strategie_utilisee: string;
    detail_pages: PageStats[];
}

export interface ExtractDocumentResponse {
    success: boolean;
    filename: string;
    format?: 'pdf' | 'docx';
    total_blocs: number;
    contenu: DocumentBloc[];
    statistiques?: ExtractionStats;
}

export interface ConvertPdfResponse {
    success: boolean;
    filename_source: string;
    filename_docx: string;
    statistiques: ExtractionStats;
    message: string;
}

export interface ExtractTariffCodesResponse {
    success: boolean;
    filename: string;
    nb_lignes_trouvees: number;
    donnees: { [key: string]: any }[]; // Lignes JSON complètes
}

export interface NormalizeLabelsResponse {
    success: boolean;
    mapping_utilise?: string;
    nb_lignes_normalisees: number;
    donnees: { [key: string]: any }[];
}
