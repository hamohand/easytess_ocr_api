// entity-creator.component.ts
import { Component, signal, inject, ElementRef, ViewChild, AfterViewInit, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../services/entity.service';
import { Zone, Entite, CadreReference, EtiquetteReference } from '../services/models';

interface ZoneDrawing extends Zone {
    id: number;
    valeurs_str?: string; // Pour le binding l'input (comma separated)
}

// Interface pour le binding UI des étiquettes
interface EtiquetteDrawing {
    labels_str: string;      // Texte comma-separated pour l'input
    position_base: [number, number];
    template_coords?: [number, number, number, number]; // Image template region
    template_preview?: string; // Base64 preview of the template
    detected_bbox?: [number, number, number, number]; // Bounding box detected by OCR/Image matching
}

@Component({
    selector: 'app-entity-creator',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './entity-creator.component.html',
    styleUrls: ['./entity-creator.component.css']
})
export class EntityCreatorComponent implements AfterViewInit, OnInit {
    private entityService = inject(EntityService);

    @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    @ViewChild('imageInput') imageInputRef!: ElementRef<HTMLInputElement>;

    // Signals - Création
    entityName = signal<string>('');
    entityDescription = signal<string>('');
    uploadedImageFilename = signal<string>('');
    imageUrl = signal<string>('');
    zones = signal<ZoneDrawing[]>([]);
    currentZoneName = signal<string>('');
    isDrawing = signal<boolean>(false);
    isSaving = signal<boolean>(false);
    errorMessage = signal<string>('');
    successMessage = signal<string>('');

    // NOUVEAU: Signaux pour Cadre de Référence (4 étiquettes)
    // HAUT : pour déterminer le point le plus haut (Y min)
    cadreHaut = signal<EtiquetteDrawing>({ labels_str: '', position_base: [0.5, 0] });
    // DROITE : pour déterminer le point le plus à droite (X max)
    cadreDroite = signal<EtiquetteDrawing>({ labels_str: '', position_base: [1, 0.5] });
    // GAUCHE : pour déterminer le point le plus à gauche (X min)
    cadreGauche = signal<EtiquetteDrawing>({ labels_str: '', position_base: [0, 0.5] });
    // BAS : pour déterminer le point le plus bas (Y max)
    cadreBas = signal<EtiquetteDrawing>({ labels_str: '', position_base: [0.5, 1] });

    // Paramètres calculés du cadre de référence
    cadreParams = signal<{
        largeur: number;   // Width relative (Xmax - Xmin)
        hauteur: number;   // Height relative (Ymax - Ymin)
        x_min: number;
        y_min: number;
        largeur_px: number; // Valeur absolue en pixels
        hauteur_px: number; // Valeur absolue en pixels
        angle: number;      // Angle (toujours 0 pour AABB)
    } | null>(null);

    // Signals - Gestion des entités existantes
    entites = signal<Entite[]>([]);
    isLoadingEntites = signal<boolean>(false);
    editMode = signal<boolean>(false);
    editingEntityName = signal<string>(''); // Nom de l'entité en cours d'édition

    // NOUVEAU: Mode de sélection visuelle pour le cadre
    activeReferenceSelection = signal<'haut' | 'droite' | 'gauche' | 'bas' | null>(null);
    isDetecting = signal<boolean>(false); // État de détection OCR en cours

    // NOUVEAU: Mode de sélection d'image template pour ancre
    anchorTemplateSelection = signal<'haut' | 'droite' | 'gauche' | 'bas' | null>(null);

    // Canvas state
    private ctx: CanvasRenderingContext2D | null = null;
    private img: HTMLImageElement | null = null;
    private imgWidth = 0;  // Original image width (for coordinate conversion)
    private imgHeight = 0; // Original image height (for coordinate conversion)
    private startX = 0;
    private startY = 0;
    private currentRect: { x: number; y: number; width: number; height: number } | null = null;

    ngOnInit() {
        this.chargerEntites();
    }

    ngAfterViewInit() {
        // Canvas sera initialisé quand l'image sera chargée
    }

    onImageSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            const isPDF = file.type === 'application/pdf';

            if (isPDF) {
                // Pour les PDF, on doit attendre la conversion serveur
                this.errorMessage.set('');
                this.successMessage.set('📄 Conversion du PDF en cours...');
                this.uploadImage(file, true); // true = charger l'image après upload
            } else {
                // Pour les images, affichage local immédiat
                const localUrl = URL.createObjectURL(file);
                this.imageUrl.set(localUrl);

                // Attendre que Angular rende le canvas
                setTimeout(() => {
                    this.loadImageOnCanvas(localUrl);
                }, 0);

                // Upload en background
                this.uploadImage(file, false);
            }
        }
    }

    uploadImage(file: File, loadAfterUpload: boolean = false) {
        this.errorMessage.set('');
        this.entityService.uploadImageEntite(file).subscribe({
            next: (response) => {
                this.uploadedImageFilename.set(response.filename);
                console.log('✅ Image uploadée sur le serveur:', response.filename);

                if (loadAfterUpload) {
                    // Pour les PDF, charger l'image convertie depuis le serveur
                    this.successMessage.set('✅ PDF converti avec succès');
                    this.imageUrl.set(response.image_url);

                    setTimeout(() => {
                        this.loadImageOnCanvas(response.image_url);
                    }, 100);

                    setTimeout(() => this.successMessage.set(''), 2000);
                }
            },
            error: (err) => {
                this.errorMessage.set('Erreur upload: ' + err.message);
            }
        });
    }

    loadImageOnCanvas(url: string) {
        console.log('Chargement image depuis URL:', url);
        const img = new Image();
        // img.crossOrigin = "Anonymous"; // Désactivé pour éviter les erreurs CORS sur les fichiers statiques

        img.onload = () => {
            this.img = img;
            // Store original image dimensions for coordinate conversion
            this.imgWidth = img.width;
            this.imgHeight = img.height;

            const canvas = this.canvasRef.nativeElement;

            // Initialiser le contexte du canvas (important car le canvas n'existe qu'après le rendu @if)
            this.ctx = canvas.getContext('2d');

            // Resize canvas to fit image
            const maxWidth = 800;
            const scale = Math.min(1, maxWidth / img.width);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;

            console.log(`📐 Image dimensions: ${this.imgWidth}x${this.imgHeight}, Canvas: ${canvas.width}x${canvas.height}`);
            this.redrawCanvas();
        };

        img.onerror = (e) => {
            console.error('Erreur chargement image:', url, e);
            this.errorMessage.set(`Impossible de charger l'image. Vérifiez que le backend est accessible. URL: ${url}`);
        };

        img.src = url;
    }

    /**
     * Active le mode de sélection visuelle pour une étiquette du cadre
     */
    startReferenceSelection(type: 'haut' | 'droite' | 'gauche' | 'bas') {
        this.activeReferenceSelection.set(type);
        // Curseur en mode cible
        if (this.canvasRef) {
            this.canvasRef.nativeElement.style.cursor = 'crosshair';
        }
    }

    /**
     * Active le mode de sélection d'image template pour une ancre
     */
    startAnchorTemplateSelection(type: 'haut' | 'droite' | 'gauche' | 'bas') {
        this.anchorTemplateSelection.set(type);
        // Curseur en mode sélection de zone
        if (this.canvasRef) {
            this.canvasRef.nativeElement.style.cursor = 'crosshair';
        }
        this.successMessage.set(`📷 Dessinez un rectangle autour de l'image à utiliser comme ancre ${type.toUpperCase()}`);
    }

    /**
     * Efface le template image d'une ancre
     */
    clearAnchorTemplate(type: 'haut' | 'droite' | 'gauche' | 'bas') {
        if (type === 'haut') {
            this.cadreHaut.update(c => ({ ...c, template_coords: undefined }));
        } else if (type === 'droite') {
            this.cadreDroite.update(c => ({ ...c, template_coords: undefined }));
        } else if (type === 'gauche') {
            this.cadreGauche.update(c => ({ ...c, template_coords: undefined }));
        } else if (type === 'bas') {
            this.cadreBas.update(c => ({ ...c, template_coords: undefined }));
        }
        this.redrawCanvas();
    }

    /**
     * Vérifie si une ancre a un template image défini
     */
    hasAnchorTemplate(type: 'haut' | 'droite' | 'gauche' | 'bas'): boolean {
        if (type === 'haut') return !!this.cadreHaut().template_coords;
        if (type === 'droite') return !!this.cadreDroite().template_coords;
        if (type === 'gauche') return !!this.cadreGauche().template_coords;
        if (type === 'bas') return !!this.cadreBas().template_coords;
        return false;
    }

    onMouseDown(event: MouseEvent) {
        if (!this.img) return;

        const canvas = this.canvasRef.nativeElement;
        const rect = canvas.getBoundingClientRect();
        const mouseX = event.clientX - rect.left;
        const mouseY = event.clientY - rect.top;

        // Si mode sélection de référence actif
        const selectionType = this.activeReferenceSelection();
        if (selectionType) {
            // Convertir en coordonnées relatives (0-1)
            const relX = parseFloat((mouseX / canvas.width).toFixed(4));
            const relY = parseFloat((mouseY / canvas.height).toFixed(4));

            // Mettre à jour l'étiquette correspondante
            if (selectionType === 'haut') {
                this.cadreHaut.update(c => ({ ...c, position_base: [relX, relY] }));
            } else if (selectionType === 'droite') {
                this.cadreDroite.update(c => ({ ...c, position_base: [relX, relY] }));
            } else if (selectionType === 'gauche') {
                this.cadreGauche.update(c => ({ ...c, position_base: [relX, relY] }));
            } else if (selectionType === 'bas') {
                this.cadreBas.update(c => ({ ...c, position_base: [relX, relY] }));
            }

            console.log(`📍 Position ${selectionType} définie à: [${relX}, ${relY}]`);

            // Recalculer les paramètres
            this.calculerParametresCadre();

            // Désactiver le mode sélection
            this.activeReferenceSelection.set(null);
            canvas.style.cursor = 'default';
            this.redrawCanvas();
            return; // Arrêter ici, pas de dessin de zone
        }

        this.startX = mouseX;
        this.startY = mouseY;
        this.isDrawing.set(true);
    }

    onMouseMove(event: MouseEvent) {
        if (!this.isDrawing() || !this.img) return;

        const canvas = this.canvasRef.nativeElement;
        const rect = canvas.getBoundingClientRect();
        const currentX = event.clientX - rect.left;
        const currentY = event.clientY - rect.top;

        this.currentRect = {
            x: Math.min(this.startX, currentX),
            y: Math.min(this.startY, currentY),
            width: Math.abs(currentX - this.startX),
            height: Math.abs(currentY - this.startY)
        };

        this.redrawCanvas();
    }

    onMouseUp(event: MouseEvent) {
        if (!this.isDrawing() || !this.currentRect) return;

        this.isDrawing.set(false);

        // Only process if rectangle has minimum size
        if (this.currentRect.width > 10 && this.currentRect.height > 10) {
            // Get canvas dimensions
            const canvas = this.canvasRef.nativeElement;
            const canvasWidth = canvas.width;
            const canvasHeight = canvas.height;

            // Convert canvas pixel coordinates to relative coordinates (0.0-1.0)
            const x1_rel = this.currentRect.x / canvasWidth;
            const y1_rel = this.currentRect.y / canvasHeight;
            const x2_rel = (this.currentRect.x + this.currentRect.width) / canvasWidth;
            const y2_rel = (this.currentRect.y + this.currentRect.height) / canvasHeight;

            const finalCoords: [number, number, number, number] = [
                parseFloat(x1_rel.toFixed(4)),
                parseFloat(y1_rel.toFixed(4)),
                parseFloat(x2_rel.toFixed(4)),
                parseFloat(y2_rel.toFixed(4))
            ];

            // NOUVEAU: Mode sélection de template image pour ancre
            const templateType = this.anchorTemplateSelection();
            if (templateType) {
                console.log(`📷 Template capturé pour ancre ${templateType}:`, finalCoords);

                // Calculer le centre du template pour mettre à jour position_base également
                // finalCoords = [x1, y1, x2, y2]
                const centerX = parseFloat(((finalCoords[0] + finalCoords[2]) / 2).toFixed(4));
                const centerY = parseFloat(((finalCoords[1] + finalCoords[3]) / 2).toFixed(4));
                const centerPos: [number, number] = [centerX, centerY];

                // Générer la preview image (Base64)
                let previewUrl = '';
                if (this.img) {
                    const tempCanvas = document.createElement('canvas');
                    const imgW = this.img.width; // Dimensions naturelles si chargée en mémoire
                    const imgH = this.img.height;

                    // Coordonnées en pixels image source
                    const sx = finalCoords[0] * imgW;
                    const sy = finalCoords[1] * imgH;
                    const sw = (finalCoords[2] - finalCoords[0]) * imgW;
                    const sh = (finalCoords[3] - finalCoords[1]) * imgH;

                    tempCanvas.width = sw;
                    tempCanvas.height = sh;
                    const ctx = tempCanvas.getContext('2d');
                    if (ctx) {
                        ctx.drawImage(this.img, sx, sy, sw, sh, 0, 0, sw, sh);
                        previewUrl = tempCanvas.toDataURL('image/png');
                    }
                }

                // Mettre à jour l'étiquette correspondante avec les coordonnées du template ET la position de base ET la preview
                if (templateType === 'haut') {
                    this.cadreHaut.update(c => ({ ...c, template_coords: finalCoords, position_base: centerPos, template_preview: previewUrl }));
                } else if (templateType === 'droite') {
                    this.cadreDroite.update(c => ({ ...c, template_coords: finalCoords, position_base: centerPos, template_preview: previewUrl }));
                } else if (templateType === 'gauche') {
                    this.cadreGauche.update(c => ({ ...c, template_coords: finalCoords, position_base: centerPos, template_preview: previewUrl }));
                } else if (templateType === 'bas') {
                    this.cadreBas.update(c => ({ ...c, template_coords: finalCoords, position_base: centerPos, template_preview: previewUrl }));
                }

                // Désactiver le mode de sélection template
                this.anchorTemplateSelection.set(null);
                canvas.style.cursor = 'default';
                this.successMessage.set(`✅ Template image défini pour l'ancre ${templateType.toUpperCase()} (avec aperçu)`);
                setTimeout(() => this.successMessage.set(''), 3000);

                this.currentRect = null;
                this.redrawCanvas();
                return; // Ne pas créer de zone OCR
            }

            // Mode normal: créer une zone OCR
            const zoneName = this.currentZoneName() || `Zone ${this.zones().length + 1}`;
            console.log(`✅ Zone créée (coords image):`, finalCoords);

            const zone: ZoneDrawing = {
                id: Date.now(),
                nom: zoneName,
                type: 'text', // Default type
                lang: 'ara+fra', // Default language
                preprocess: 'auto', // Default preprocessing
                valeurs_str: '', // Init flat values
                coords: finalCoords
            };

            this.zones.update(zones => [...zones, zone]);
            this.currentZoneName.set('');
        }

        this.currentRect = null;
        this.redrawCanvas();
    }

    redrawCanvas() {
        if (!this.ctx || !this.img) return;

        const canvas = this.canvasRef.nativeElement;
        this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.ctx.drawImage(this.img, 0, 0, canvas.width, canvas.height);

        // Dessiner le cadre de référence si défini
        this.drawCadreReference(canvas);

        // Draw existing zones (convert relative coords to canvas pixels)
        this.zones().forEach((zone, index) => {
            let [x1, y1, x2, y2] = zone.coords;

            // Convert relative coordinates (0-1) to canvas pixels
            // Note: Les zones en mémoire sont toujours en coords relatives à l'image
            if (x1 <= 1.0 && y1 <= 1.0 && x2 <= 1.0 && y2 <= 1.0) {
                x1 = x1 * canvas.width;
                y1 = y1 * canvas.height;
                x2 = x2 * canvas.width;
                y2 = y2 * canvas.height;
            }

            this.drawZone(x1, y1, x2 - x1, y2 - y1, zone.nom, index + 1, '#00ff00');
        });

        // Draw current rectangle being drawn
        if (this.currentRect) {
            this.drawZone(
                this.currentRect.x,
                this.currentRect.y,
                this.currentRect.width,
                this.currentRect.height,
                this.currentZoneName() || 'Nouvelle zone',
                this.zones().length + 1,
                '#ff0000'
            );
        }
    }

    /**
     * Dessine le cadre de référence sur le canvas (ORIGINE, LARGEUR, HAUTEUR)
     */
    /**
     * Dessine le cadre de référence sur le canvas (HAUT, DROITE, GAUCHE, BAS)
     */
    drawCadreReference(canvas: HTMLCanvasElement) {
        if (!this.ctx) return;

        // DEBUG: Log anchor states
        // console.log('🔍 drawCadreReference called', this.cadreHaut(), this.cadreDroite(), this.cadreGauche(), this.cadreBas());

        if (!this.isCadreValide()) {
            return;
        }

        const hautPos = this.cadreHaut().position_base;
        const droitePos = this.cadreDroite().position_base;
        const gauchePos = this.cadreGauche().position_base;
        const basPos = this.cadreBas().position_base;

        // Convertir en pixels canvas
        const hPos = { x: hautPos[0] * canvas.width, y: hautPos[1] * canvas.height };
        const dPos = { x: droitePos[0] * canvas.width, y: droitePos[1] * canvas.height };
        const gPos = { x: gauchePos[0] * canvas.width, y: gauchePos[1] * canvas.height };
        const bPos = { x: basPos[0] * canvas.width, y: basPos[1] * canvas.height };

        // Calculer les limites du cadre
        const yMin = hPos.y;
        const yMax = bPos.y;
        const xMin = gPos.x;
        const xMax = dPos.x;

        // Dessiner le rectangle du cadre calculé (AABB Global)
        this.ctx.strokeStyle = '#ff00ff';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([8, 4]);
        this.ctx.beginPath();
        this.ctx.rect(xMin, yMin, xMax - xMin, yMax - yMin);
        this.ctx.stroke();
        // NOUVEAU: Remplissage semi-transparent pour visualiser l'aire effective
        this.ctx.fillStyle = 'rgba(255, 0, 255, 0.1)';
        this.ctx.fill();
        this.ctx.setLineDash([]);

        // Dessiner les limites étendues (lignes guides)
        this.ctx.strokeStyle = 'rgba(255, 0, 255, 0.3)';
        this.ctx.lineWidth = 1;

        // Helper pour dessiner les BBoxes détectées
        const drawDetectedBBox = (bbox: [number, number, number, number] | undefined, color: string) => {
            if (!bbox || !this.img || !this.ctx) return;
            const [bx, by, bx2, by2] = bbox;
            // Conversion pixels image -> pixels canvas
            const rX = canvas.width / this.img.width;
            const rY = canvas.height / this.img.height;

            const rx = bx * rX;
            const ry = by * rY;
            const rw = (bx2 - bx) * rX;
            const rh = (by2 - by) * rY;

            this.ctx.save();
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 2;
            this.ctx.strokeRect(rx, ry, rw, rh);
            this.ctx.fillStyle = color + '44'; // Transparence
            this.ctx.fillRect(rx, ry, rw, rh);
            this.ctx.restore();
        };

        // Dessiner les bboxes individuelles des ancres détectées
        drawDetectedBBox(this.cadreHaut().detected_bbox, '#ff9800');
        drawDetectedBBox(this.cadreDroite().detected_bbox, '#2196f3');
        drawDetectedBBox(this.cadreGauche().detected_bbox, '#9c27b0');
        drawDetectedBBox(this.cadreBas().detected_bbox, '#4caf50');

        // Lignes guides infinies
        this.ctx.beginPath(); this.ctx.moveTo(0, yMin); this.ctx.lineTo(canvas.width, yMin); this.ctx.stroke();
        this.ctx.beginPath(); this.ctx.moveTo(0, yMax); this.ctx.lineTo(canvas.width, yMax); this.ctx.stroke();
        this.ctx.beginPath(); this.ctx.moveTo(xMin, 0); this.ctx.lineTo(xMin, canvas.height); this.ctx.stroke();
        this.ctx.beginPath(); this.ctx.moveTo(xMax, 0); this.ctx.lineTo(xMax, canvas.height); this.ctx.stroke();

        // Marqueurs pour les 4 étiquettes (Centres)
        this.drawMarker(hPos.x, hPos.y, 'Haut', '#ff9800');
        this.drawMarker(dPos.x, dPos.y, 'Dr.', '#2196f3');
        this.drawMarker(gPos.x, gPos.y, 'G', '#4caf50');
        this.drawMarker(bPos.x, bPos.y, 'Bas', '#f44336');

        console.log('✅ Frame drawn successfully');
    }

    private drawMarker(x: number, y: number, label: string, color: string) {
        if (!this.ctx) return;
        this.ctx.fillStyle = color;
        this.ctx.beginPath();
        this.ctx.arc(x, y, 6, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.fillStyle = 'white';
        this.ctx.font = 'bold 10px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(label[0], x, y);

        // Label externe
        this.ctx.fillStyle = color;
        this.ctx.fillText(label, x, y - 12);
    }


    drawZone(x: number, y: number, width: number, height: number, name: string, num: number, color: string) {
        if (!this.ctx) return;

        // Rectangle
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 3;
        this.ctx.strokeRect(x, y, width, height);

        // Background for text
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        this.ctx.fillRect(x, y - 25, 200, 25);

        // Text
        this.ctx.fillStyle = 'white';
        this.ctx.font = '14px Arial';
        this.ctx.fillText(`${num}. ${name}`, x + 5, y - 8);
    }

    deleteZone(id: number) {
        this.zones.update(zones => zones.filter(z => z.id !== id));
        this.redrawCanvas();
    }

    onZoneChanged() {
        // Redessiner le canvas quand une zone est modifiée (nom ou coordonnées)
        this.redrawCanvas();
    }

    // ==================== GESTION DU CADRE DE RÉFÉRENCE ====================

    /**
     * Vérifie si le cadre de référence est valide (les 3 étiquettes ont des labels)
     */
    /**
     * Vérifie si le cadre de référence est valide (les 4 étiquettes ont des labels)
     */
    /**
     * Le cadre est toujours valide maintenant (si vide = plein écran)
     */
    isCadreValide(): boolean {
        return true;
    }

    /**
     * Détecte automatiquement les positions des étiquettes via OCR
     */
    detecterEtiquettes(): void {
        const filename = this.uploadedImageFilename();
        if (!filename) {
            this.errorMessage.set('Veuillez d\'abord uploader une image');
            return;
        }

        // Construire l'objet des étiquettes à chercher (labels texte ET/OU templates image)
        const etiquettes: any = {};

        const addAnchorConfig = (type: 'haut' | 'droite' | 'gauche' | 'bas') => {
            let labels: string[] = [];
            let template_coords: [number, number, number, number] | undefined = undefined;

            if (type === 'haut') {
                labels = this.cadreHaut().labels_str.split(',').map(s => s.trim()).filter(s => s);
                template_coords = this.cadreHaut().template_coords;
            } else if (type === 'droite') {
                labels = this.cadreDroite().labels_str.split(',').map(s => s.trim()).filter(s => s);
                template_coords = this.cadreDroite().template_coords;
            } else if (type === 'gauche') {
                labels = this.cadreGauche().labels_str.split(',').map(s => s.trim()).filter(s => s);
                template_coords = this.cadreGauche().template_coords;
            } else if (type === 'bas') {
                labels = this.cadreBas().labels_str.split(',').map(s => s.trim()).filter(s => s);
                template_coords = this.cadreBas().template_coords;
            }

            if (labels.length > 0 || template_coords) {
                etiquettes[type] = {
                    labels: labels,
                    template_coords: template_coords
                };
            }
        };

        addAnchorConfig('haut');
        addAnchorConfig('droite');
        addAnchorConfig('gauche');
        addAnchorConfig('bas');

        // Si aucune étiquette n'est définie (ni texte ni image), on reset aux bords par défaut (Plein écran)
        if (Object.keys(etiquettes).length === 0) {
            console.log('⚠️ Aucune étiquette définie -> Utilisation des bords par défaut (Plein écran)');
            this.cadreHaut.update(c => ({ ...c, position_base: [0.5, 0] }));
            this.cadreDroite.update(c => ({ ...c, position_base: [1, 0.5] }));
            this.cadreGauche.update(c => ({ ...c, position_base: [0, 0.5] }));
            this.cadreBas.update(c => ({ ...c, position_base: [0.5, 1] }));

            this.calculerParametresCadre();
            this.redrawCanvas();
            this.successMessage.set('✅ Cadre défini sur l\'image entière (par défaut)');
            setTimeout(() => this.successMessage.set(''), 3000);
            return;
        }

        this.isDetecting.set(true);
        this.errorMessage.set('');

        this.entityService.detecterEtiquettes(filename, etiquettes).subscribe({
            next: (result) => {
                this.isDetecting.set(false);

                console.log('🔍 Backend detection result:', result);
                console.log('📍 Positions from backend:', result.positions);

                if (result.success && result.positions) {
                    // Mettre à jour les positions détectées
                    // Mettre à jour les positions détectées ou réinitialiser par défaut
                    if (result.positions['haut']?.found) {
                        console.log('  ✅ Updating HAUT:', result.positions['haut']);
                        this.cadreHaut.update(c => ({
                            ...c,
                            position_base: [result.positions['haut'].x, result.positions['haut'].y],
                            detected_bbox: result.positions['haut'].bbox
                        }));
                    } else {
                        // Reset default (Edge)
                        console.log('  defaults HAUT');
                        this.cadreHaut.update(c => ({ ...c, position_base: [0.5, 0], detected_bbox: undefined }));
                    }

                    if (result.positions['droite']?.found) {
                        console.log('  ✅ Updating DROITE:', result.positions['droite']);
                        this.cadreDroite.update(c => ({
                            ...c,
                            position_base: [result.positions['droite'].x, result.positions['droite'].y],
                            detected_bbox: result.positions['droite'].bbox
                        }));
                    } else {
                        // Reset default (Edge)
                        console.log('  defaults DROITE');
                        this.cadreDroite.update(c => ({ ...c, position_base: [1, 0.5], detected_bbox: undefined }));
                    }

                    if (result.positions['gauche']?.found) {
                        console.log('  ✅ Updating GAUCHE:', result.positions['gauche']);
                        this.cadreGauche.update(c => ({
                            ...c,
                            position_base: [result.positions['gauche'].x, result.positions['gauche'].y],
                            detected_bbox: result.positions['gauche'].bbox
                        }));
                    } else {
                        // Reset default (Edge)
                        console.log('  defaults GAUCHE');
                        this.cadreGauche.update(c => ({ ...c, position_base: [0, 0.5], detected_bbox: undefined }));
                    }

                    if (result.positions['bas']?.found) {
                        console.log('  ✅ Updating BAS:', result.positions['bas']);
                        this.cadreBas.update(c => ({
                            ...c,
                            position_base: [result.positions['bas'].x, result.positions['bas'].y],
                            detected_bbox: result.positions['bas'].bbox
                        }));
                    } else {
                        // Reset default (Edge)
                        console.log('  defaults BAS');
                        this.cadreBas.update(c => ({ ...c, position_base: [0.5, 1], detected_bbox: undefined }));
                    }

                    // Recalculer les paramètres
                    this.calculerParametresCadre();
                    this.redrawCanvas();

                    if (result.toutes_trouvees) {
                        this.successMessage.set('✅ Toutes les étiquettes ont été détectées !');
                    } else {
                        const nonTrouvees = Object.entries(result.positions)
                            .filter(([_, v]) => !v.found)
                            .map(([k, _]) => k.toUpperCase());
                        this.errorMessage.set(`⚠️ Étiquettes non trouvées: ${nonTrouvees.join(', ')}`);
                    }

                    setTimeout(() => this.successMessage.set(''), 3000);
                } else {
                    this.errorMessage.set(result.error || 'Erreur lors de la détection');
                }
            },
            error: (err) => {
                this.isDetecting.set(false);
                this.errorMessage.set('Erreur détection: ' + (err.error?.error || err.message));
            }
        });
    }

    /**
     * Calcule les paramètres du cadre (largeur, hauteur) à partir des positions
     */
    calculerParametresCadre(): void {
        const haut = this.cadreHaut().position_base;
        const droite = this.cadreDroite().position_base;
        const gauche = this.cadreGauche().position_base;
        const bas = this.cadreBas().position_base;

        // Largeur relative du cadre (Droite.x - Gauche.x)
        const largeurRel = Math.abs(droite[0] - gauche[0]);
        // Hauteur relative du cadre (Bas.y - Haut.y)
        const hauteurRel = Math.abs(bas[1] - haut[1]);

        // Valeurs absolues
        const largeurPx = Math.round(largeurRel * this.imgWidth);
        const hauteurPx = Math.round(hauteurRel * this.imgHeight);

        this.cadreParams.set({
            largeur: parseFloat((largeurRel * 100).toFixed(2)),
            hauteur: parseFloat((hauteurRel * 100).toFixed(2)),
            x_min: gauche[0],
            y_min: haut[1],
            largeur_px: largeurPx,
            hauteur_px: hauteurPx,
            angle: 0 // AABB est aligné
        });
    }

    // Helper pour récupérer les dimensions du cadre en 0-1
    private getCadreDimensions(): { x: number, y: number, w: number, h: number } | null {
        if (!this.isCadreValide()) return null;

        const haut = this.cadreHaut().position_base;
        const droite = this.cadreDroite().position_base;
        const gauche = this.cadreGauche().position_base;
        const bas = this.cadreBas().position_base;

        const x = gauche[0];
        const y = haut[1];
        let w = Math.abs(droite[0] - gauche[0]);
        let h = Math.abs(bas[1] - haut[1]);

        // Protection
        if (w < 0.001) w = 1;
        if (h < 0.001) h = 1;

        return { x, y, w, h };
    }

    private transformZonesToFrame(zones: Zone[]): Zone[] {
        const cadre = this.getCadreDimensions();
        if (!cadre) return zones; // Pas de cadre, on garde tel quel

        return zones.map(z => {
            const [x1, y1, x2, y2] = z.coords;
            // Conversion: (val - origin) / size
            const nx1 = (x1 - cadre.x) / cadre.w;
            const ny1 = (y1 - cadre.y) / cadre.h;
            const nx2 = (x2 - cadre.x) / cadre.w;
            const ny2 = (y2 - cadre.y) / cadre.h;

            return {
                ...z,
                coords: [nx1, ny1, nx2, ny2]
            };
        });
    }

    private transformZonesFromFrame(zones: Zone[]): Zone[] {
        const cadre = this.getCadreDimensions();
        if (!cadre) return zones;

        return zones.map(z => {
            const [nx1, ny1, nx2, ny2] = z.coords;
            // Conversion: val * size + origin
            const x1 = nx1 * cadre.w + cadre.x;
            const y1 = ny1 * cadre.h + cadre.y;
            const x2 = nx2 * cadre.w + cadre.x;
            const y2 = ny2 * cadre.h + cadre.y;

            return {
                ...z,
                coords: [x1, y1, x2, y2]
            };
        });
    }

    saveEntity() {
        const name = this.entityName();
        const rawZones = this.zones();
        const imageFilename = this.uploadedImageFilename();

        if (!name) {
            this.errorMessage.set('Veuillez entrer un nom d\'entité');
            return;
        }

        if (rawZones.length === 0) {
            this.errorMessage.set('Veuillez définir au moins une zone');
            return;
        }

        // Process zones to convert flat values string to array
        let processedZones: Zone[] = rawZones.map(z => {
            const { valeurs_str, ...rest } = z; // Remove UI helper props
            const zone: Zone = { ...rest };

            if (valeurs_str) {
                zone.valeurs_attendues = valeurs_str.split(',').map(s => s.trim()).filter(s => s);
            }
            return zone;
        });

        // NOUVEAU: Convertir les coordonnées relatives à l'image -> relatives au cadre
        if (this.isCadreValide()) {
            processedZones = this.transformZonesToFrame(processedZones);
            console.log('🔄 Zones converties vers le référentiel cadre avant sauvegarde');
        }

        // Construire le cadre de référence
        let cadre_reference: CadreReference | undefined = undefined;

        if (this.isCadreValide()) {
            const parseLabels = (str: string) =>
                str.split(',').map(l => l.trim()).filter(l => l.length > 0);

            cadre_reference = {
                haut: {
                    labels: parseLabels(this.cadreHaut().labels_str),
                    position_base: this.cadreHaut().position_base,
                    ...(this.cadreHaut().template_coords && { template_coords: this.cadreHaut().template_coords })
                },
                droite: {
                    labels: parseLabels(this.cadreDroite().labels_str),
                    position_base: this.cadreDroite().position_base,
                    ...(this.cadreDroite().template_coords && { template_coords: this.cadreDroite().template_coords })
                },
                gauche: {
                    labels: parseLabels(this.cadreGauche().labels_str),
                    position_base: this.cadreGauche().position_base,
                    ...(this.cadreGauche().template_coords && { template_coords: this.cadreGauche().template_coords })
                },
                bas: {
                    labels: parseLabels(this.cadreBas().labels_str),
                    position_base: this.cadreBas().position_base,
                    ...(this.cadreBas().template_coords && { template_coords: this.cadreBas().template_coords })
                },
                image_base_dimensions: {
                    width: this.imgWidth,
                    height: this.imgHeight
                },
                dimensions_absolues: {
                    largeur: this.cadreParams()?.largeur_px ?? 0,
                    hauteur: this.cadreParams()?.hauteur_px ?? 0,
                    angle: this.cadreParams()?.angle ?? 0
                }
            };
            console.log('📐 Cadre de référence construit:', cadre_reference);
        }

        this.isSaving.set(true);
        this.errorMessage.set('');
        this.successMessage.set('');

        this.entityService.sauvegarderEntite(
            name,
            processedZones,
            imageFilename,
            this.entityDescription(),
            cadre_reference  // Passer le cadre de référence
        ).subscribe({
            next: () => {
                this.successMessage.set(`✅ Entité "${name}" sauvegardée avec succès !`);
                this.isSaving.set(false);
                setTimeout(() => this.reset(), 2000);
            },
            error: (err) => {
                this.errorMessage.set('Erreur sauvegarde: ' + err.message);
                this.isSaving.set(false);
            }
        });
    }

    reset() {
        this.entityName.set('');
        this.entityDescription.set('');
        this.uploadedImageFilename.set('');
        this.imageUrl.set('');
        this.zones.set([]);
        // Réinitialiser les étiquettes du cadre de référence (4 anchors)
        this.cadreHaut.set({ labels_str: '', position_base: [0.5, 0] });
        this.cadreDroite.set({ labels_str: '', position_base: [1, 0.5] });
        this.cadreGauche.set({ labels_str: '', position_base: [0, 0.5] });
        this.cadreBas.set({ labels_str: '', position_base: [0.5, 1] });
        this.cadreParams.set(null);
        this.currentZoneName.set('');
        this.successMessage.set('');
        this.errorMessage.set('');
        this.editMode.set(false);
        this.editingEntityName.set('');
        this.img = null;

        if (this.ctx && this.canvasRef) {
            const canvas = this.canvasRef.nativeElement;
            this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        }

        // Recharger la liste des entités
        this.chargerEntites();
    }

    // ==================== GESTION DES ENTITÉS ====================

    chargerEntites() {
        this.isLoadingEntites.set(true);
        this.entityService.listerEntites().subscribe({
            next: (entites) => {
                this.entites.set(entites);
                this.isLoadingEntites.set(false);
            },
            error: (err) => {
                console.error('Erreur chargement entités:', err);
                this.isLoadingEntites.set(false);
            }
        });
    }

    chargerEntite(nom: string) {
        this.errorMessage.set('');
        this.entityService.getEntite(nom).subscribe({
            next: (entite) => {
                // Passer en mode édition
                this.editMode.set(true);
                this.editingEntityName.set(nom);

                // Remplir les champs
                this.entityName.set(entite.nom);
                this.entityDescription.set(entite.description || '');

                // IMPORTANT: Charger le cadre de référence AVANT les zones
                // car on a besoin du cadre pour convertir les coordonnées
                if (entite.cadre_reference) {
                    const cadre = entite.cadre_reference;

                    if (cadre.haut && cadre.droite) {
                        // Charger HAUT et DROITE (toujours présents)
                        this.cadreHaut.set({
                            labels_str: cadre.haut.labels.join(', '),
                            position_base: cadre.haut.position_base
                        });
                        this.cadreDroite.set({
                            labels_str: cadre.droite.labels.join(', '),
                            position_base: cadre.droite.position_base
                        });

                        // Migration automatique: ancien format 3-étiquettes (GAUCHE-BAS) → nouveau 4-étiquettes (GAUCHE + BAS)
                        if (cadre.gauche && cadre.bas) {
                            // Nouveau format 4 anchors: charger directement
                            this.cadreGauche.set({
                                labels_str: cadre.gauche.labels.join(', '),
                                position_base: cadre.gauche.position_base
                            });
                            this.cadreBas.set({
                                labels_str: cadre.bas.labels.join(', '),
                                position_base: cadre.bas.position_base
                            });
                            console.log('✅ Cadre 4-anchors chargé');
                        } else if (cadre.gauche_bas) {
                            // Ancien format 3 anchors: migrer GAUCHE-BAS → GAUCHE + BAS
                            // GAUCHE récupère la position X, Y du GAUCHE-BAS
                            this.cadreGauche.set({
                                labels_str: cadre.gauche_bas.labels.join(', '),
                                position_base: [cadre.gauche_bas.position_base[0], 0.5]  // X de gauche_bas, Y au milieu
                            });
                            // BAS récupère la position Y du GAUCHE-BAS
                            this.cadreBas.set({
                                labels_str: cadre.gauche_bas.labels.join(', '),
                                position_base: [0.5, cadre.gauche_bas.position_base[1]]  // X au milieu, Y de gauche_bas
                            });
                            console.log('⚠️ Migration automatique 3-anchors → 4-anchors effectuée');
                            this.errorMessage.set('⚠️ Ancien format 3-étiquettes détecté et migré automatiquement vers 4-étiquettes.');
                        }
                    } else if (cadre.origine) {
                        // Legacy format fallback (migration approximative depuis l'ancien ancien système)
                        this.cadreHaut.set({
                            labels_str: cadre.origine.labels.join(', '),
                            position_base: cadre.origine.position_base
                        });
                        if (cadre.largeur) {
                            this.cadreDroite.set({
                                labels_str: cadre.largeur.labels.join(', '),
                                position_base: cadre.largeur.position_base
                            });
                        }
                        if (cadre.hauteur) {
                            // Migrer hauteur vers GAUCHE + BAS
                            this.cadreGauche.set({
                                labels_str: cadre.hauteur.labels.join(', '),
                                position_base: [0, 0.5]
                            });
                            this.cadreBas.set({
                                labels_str: cadre.hauteur.labels.join(', '),
                                position_base: cadre.hauteur.position_base
                            });
                        }
                        this.errorMessage.set('⚠️ Format de cadre très obsolète converti. Veuillez vérifier les positions.');
                    }

                    // Calculer les paramètres du cadre
                    this.calculerParametresCadre();
                    console.log('📐 Cadre de référence chargé:', this.cadreParams());
                } else {
                    // Réinitialiser les signaux du cadre (4 anchors)
                    this.cadreHaut.set({ labels_str: '', position_base: [0.5, 0] });
                    this.cadreDroite.set({ labels_str: '', position_base: [1, 0.5] });
                    this.cadreGauche.set({ labels_str: '', position_base: [0, 0.5] });
                    this.cadreBas.set({ labels_str: '', position_base: [0.5, 1] });
                    this.cadreParams.set(null);
                }

                // Charger les zones APRÈS le cadre de référence
                let loadedZones: Zone[] = entite.zones || [];

                // NOUVEAU: Convertir frame-relative → image-relative pour l'édition
                // Les zones stockées dans le JSON sont relatives au cadre (frame-relative).
                // Pour l'édition, on doit les convertir en coordonnées relatives à l'image (image-relative).
                // Lors de la sauvegarde, transformZonesToFrame() sera appliquée pour reconvertir.
                if (entite.cadre_reference && this.isCadreValide()) {
                    loadedZones = this.transformZonesFromFrame(loadedZones);
                    console.log('🔄 Zones converties depuis le référentiel cadre vers l\'image pour édition');
                }

                // Convertir en ZoneDrawing avec valeurs_str
                const zonesDrawing: ZoneDrawing[] = loadedZones.map((z, index) => ({
                    ...z,
                    id: z.id || Date.now() + index,
                    valeurs_str: z.valeurs_attendues?.join(', ') || ''
                }));
                this.zones.set(zonesDrawing);

                // Charger l'image de référence si elle existe
                if (entite.image_reference) {
                    // Extraire juste le nom du fichier (gérer / et \ pour Windows)
                    const parts = entite.image_reference.split(/[/\\]/);
                    const filename = parts.pop() || entite.image_reference;
                    const imageUrl = `http://localhost:8082/uploads/${filename}`;
                    this.imageUrl.set(imageUrl);
                    this.uploadedImageFilename.set(filename);

                    setTimeout(() => {
                        this.loadImageOnCanvas(imageUrl);
                    }, 100);
                }

                console.log('✏️ Édition entité:', nom);
            },
            error: (err) => {
                this.errorMessage.set('Erreur chargement entité: ' + err.message);
            }
        });
    }

    supprimerEntite(nom: string) {
        if (!confirm(`Êtes-vous sûr de vouloir supprimer l'entité "${nom}" ?`)) {
            return;
        }

        this.entityService.supprimerEntite(nom).subscribe({
            next: () => {
                this.successMessage.set(`✅ Entité "${nom}" supprimée`);
                this.chargerEntites();
                setTimeout(() => this.successMessage.set(''), 3000);
            },
            error: (err) => {
                this.errorMessage.set('Erreur suppression: ' + err.message);
            }
        });
    }

    cancelEdit() {
        this.reset();
    }
}

