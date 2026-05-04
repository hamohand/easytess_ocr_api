// models.ts - Interfaces TypeScript pour l'API EasyTess

export interface Zone {
    id?: number;
    nom: string;
    coords: [number, number, number, number]; // [x1, y1, x2, y2]
    type?: 'text' | 'qrcode' | 'barcode';
    lang?: 'fra' | 'ara' | 'ara+fra' | 'eng';  // Langue OCR pour cette zone
    preprocess?: 'auto' | 'arabic_textured' | 'latin_simple' | 'none';  // Mode prétraitement
    char_filter?: 'none' | 'alpha_only' | 'digits_only' | 'alphanum';  // Filtre post-OCR sur les caractères
    expected_format?: 'auto' | 'single_line' | 'raw_line' | 'block' | 'single_word'; // Stratégie PSM
    margin?: number;  // Marge de sécurité en pixels (retrait sur chaque bord avant OCR)
    valeurs_attendues?: string[];
}

// Étiquette de référence pour le cadre utile
export interface EtiquetteReference {
    labels: string[];                        // Textes à chercher (ex: ["PASSPORT", "PASSEPORT"])
    position_base: [number, number];         // Position (x, y) sur l'image de base (0-1)
    template_coords?: [number, number, number, number]; // NEW: Image template region [x1, y1, x2, y2] relative (0-1)
    manuel_formula?: string;                 // NEW: Formule de secours experte en pixels (ex: "G + largeur")
    fallback_formula?: string;               // Formule de secours si OCR+Image échouent (ex: "H + 0.40")
                                             // Variables: H (haut.y), B (bas.y), G (gauche.x), D (droite.x)
}

// Cadre de référence pour définir le système de coordonnées
export interface CadreReference {
    // NOUVEAU SYSTÈME (HAUT, DROITE, GAUCHE, BAS) - 4 étiquettes
    haut: EtiquetteReference;        // Y min
    droite: EtiquetteReference;      // X max
    gauche: EtiquetteReference;      // X min
    bas: EtiquetteReference;         // Y max

    // Backward compatibility (deprecated - old 3-anchor system)
    gauche_bas?: EtiquetteReference;  // X min, Y max (sera migré automatiquement)

    // Legacy support (deprecated)
    origine?: EtiquetteReference;
    largeur?: EtiquetteReference;
    hauteur?: EtiquetteReference;

    // Dimensions de l'image de référence
    image_base_dimensions?: {
        width: number;
        height: number;
    };

    // Nouvelle propriété: Dimensions absolues et angle (L, H, A)
    dimensions_absolues?: {
        largeur: number;  // en pixels
        hauteur: number;  // en pixels
        angle: number;    // en degrés
    };
}

// Legacy: Ancre pour le repère géométrique (deprecated, use CadreReference)
export interface AncreRepere {
    id: string;
    labels: string[];
    position_base: [number, number];
}

export interface Repere {
    ancres: AncreRepere[];
    image_base_dimensions?: { width: number; height: number };
}

export interface Entite {
    nom: string;
    description?: string;
    date_creation?: string;
    image_reference?: string;
    zones: Zone[];
    cadre_reference?: CadreReference;        // NOUVEAU: Cadre de référence à 3 étiquettes
    repere?: Repere;                         // Legacy (deprecated)
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
    cadre_detecte?: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
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

// Batch OCR Analysis
export interface BatchUploadResponse {
    success: boolean;
    files: { filename: string; saved_filename: string; error?: string }[];
}

export interface BatchFileResult {
    filename: string;
    success: boolean;
    resultats?: { [zoneName: string]: ResultatOCR };
    alertes?: string[];
    stats_moteurs?: { [moteur: string]: number };
    error?: string;
}

export interface BatchAnalyseResponse {
    success: boolean;
    total: number;
    reussis: number;
    echoues: number;
    resultats_batch: BatchFileResult[];
}

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
    nb_lignes_normalisees: number;
    donnees: { [key: string]: any }[];
}

// ─── Invoice extraction models ───────────────────────────

export interface InvoiceArticle {
    designation: string;
    confiance: number;
    position_y: number;
    nb_mots: number;
    page?: number;
}

export interface InvoiceColumnBounds {
    x_min: number;
    x_max: number;
}

export interface InvoiceExtractionResponse {
    success: boolean;
    filename: string;
    articles: InvoiceArticle[];
    nb_articles: number;
    en_tete_detecte: string | null;
    colonne_designation: InvoiceColumnBounds | null;
    total_mots_ocr: number;
    total_lignes: number;
    image_dimensions?: { width: number; height: number };
    nb_pages?: number;
    pages?: InvoicePageResult[];
    error?: string | null;
    debug?: { lignes_ocr?: string[] };
}

export interface InvoicePageResult {
    page: number;
    nb_articles: number;
    en_tete_detecte: string | null;
    articles: InvoiceArticle[];
}

