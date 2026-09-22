// entity-anchor-creator.component.ts
import { Component, signal, inject, ElementRef, ViewChild, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../../services/entity.service';
import { AnchorZone, AnchorEntite } from '../../services/models';

interface AnchorZoneDrawing extends AnchorZone {
    valeurs_str?: string;
}

@Component({
    selector: 'app-entity-anchor-creator',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './entity-anchor-creator.component.html',
    styleUrls: ['./entity-anchor-creator.component.css']
})
export class EntityAnchorCreatorComponent implements OnInit {
    private entityService = inject(EntityService);

    @ViewChild('imageCanvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    @ViewChild('imageInput') imageInputRef!: ElementRef<HTMLInputElement>;

    // Signals - Création
    entityName = signal<string>('');
    entityDescription = signal<string>('');
    imageUrl = signal<string>('');
    uploadedImageFilename = signal<string>('');
    zones = signal<AnchorZoneDrawing[]>([]);
    isDrawing = signal<boolean>(false);
    isSaving = signal<boolean>(false);
    isLoading = signal<boolean>(false);
    errorMessage = signal<string>('');
    successMessage = signal<string>('');

    // Signals - Gestion des entités existantes
    entites = signal<AnchorEntite[]>([]);
    editMode = signal<boolean>(false);
    editingEntityName = signal<string>('');

    // Canvas state
    private ctx: CanvasRenderingContext2D | null = null;
    private img: HTMLImageElement | null = null;
    private imgWidth = 0;
    private imgHeight = 0;
    private startX = 0;
    private startY = 0;
    private currentRect: { x: number; y: number; width: number; height: number } | null = null;

    ngOnInit() {
        this.chargerEntites();
    }

    // ==================== IMAGE UPLOAD ====================

    onImageSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files?.length) return;

        const file = input.files[0];
        this.errorMessage.set('');
        this.successMessage.set('');
        const isPDF = file.type === 'application/pdf';

        if (isPDF) {
            // PDF : il faut attendre la conversion côté serveur
            this.successMessage.set('📄 Conversion du PDF en cours...');
            this.entityService.uploadImageEntite(file).subscribe({
                next: (resp) => {
                    this.uploadedImageFilename.set(resp.filename);
                    this.imageUrl.set(resp.image_url);
                    setTimeout(() => this.loadImageOnCanvas(resp.image_url), 100);
                    this.successMessage.set(`✅ PDF converti`);
                    setTimeout(() => this.successMessage.set(''), 3000);
                },
                error: (err) => {
                    this.errorMessage.set('Erreur upload: ' + (err.error?.message || err.message));
                }
            });
        } else {
            // Image : affichage local immédiat, upload en arrière-plan
            const localUrl = URL.createObjectURL(file);
            this.imageUrl.set(localUrl);
            setTimeout(() => this.loadImageOnCanvas(localUrl), 0);

            this.entityService.uploadImageEntite(file).subscribe({
                next: (resp) => {
                    this.uploadedImageFilename.set(resp.filename);
                    this.successMessage.set(`✅ Image « ${resp.filename} » uploadée`);
                    setTimeout(() => this.successMessage.set(''), 3000);
                },
                error: (err) => {
                    this.errorMessage.set('Erreur upload: ' + (err.error?.message || err.message));
                }
            });
        }
    }

    // ==================== CANVAS LOGIC ====================

    loadImageOnCanvas(url: string) {
        const img = new Image();
        img.crossOrigin = 'Anonymous';

        img.onload = () => {
            this.img = img;
            this.imgWidth = img.width;
            this.imgHeight = img.height;

            const canvas = this.canvasRef.nativeElement;
            this.ctx = canvas.getContext('2d');

            const maxWidth = 800;
            const scale = Math.min(1, maxWidth / img.width);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;

            this.redrawCanvas();
        };

        img.onerror = () => {
            this.errorMessage.set(`Impossible de charger l'image. Vérifiez que le backend est accessible.`);
        };

        img.src = url;
    }

    onMouseDown(event: MouseEvent) {
        if (!this.img) return;

        const canvas = this.canvasRef.nativeElement;
        const rect = canvas.getBoundingClientRect();
        this.startX = event.clientX - rect.left;
        this.startY = event.clientY - rect.top;
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

        if (this.currentRect.width > 10 && this.currentRect.height > 10) {
            const canvas = this.canvasRef.nativeElement;
            const canvasWidth = canvas.width;
            const canvasHeight = canvas.height;

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

            const zone: AnchorZoneDrawing = {
                id: Date.now(),
                nom: `Zone ${this.zones().length + 1}`,
                anchor_text: '',
                anchor_direction: 'droite',
                lang: 'ara+fra',
                char_filter: 'none',
                expected_format: 'auto',
                preprocess: 'auto',
                margin: 0,
                coords: finalCoords
            };

            this.zones.update(zones => [...zones, zone]);
        }

        this.currentRect = null;
        this.redrawCanvas();
    }

    redrawCanvas() {
        if (!this.ctx || !this.img) return;

        const canvas = this.canvasRef.nativeElement;
        this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        this.ctx.drawImage(this.img, 0, 0, canvas.width, canvas.height);

        // Draw existing zones
        this.zones().forEach((zone, index) => {
            let [x1, y1, x2, y2] = zone.coords;

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
                'Nouvelle zone',
                this.zones().length + 1,
                '#ff0000'
            );
        }
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

    // ==================== ENTITÉS EXISTANTES ====================

    chargerEntites() {
        this.isLoading.set(true);
        this.entityService.listerEntitesAncre().subscribe({
            next: (data) => {
                this.entites.set(data);
                this.isLoading.set(false);
            },
            error: (err) => {
                this.errorMessage.set('Erreur chargement: ' + (err.error?.message || err.message));
                this.isLoading.set(false);
            }
        });
    }

    chargerEntite(nom: string) {
        this.isLoading.set(true);
        this.entityService.getEntite(nom).subscribe({
            next: (data: any) => {
                this.entityName.set(data.nom);
                this.entityDescription.set(data.description || '');
                this.editMode.set(true);
                this.editingEntityName.set(data.nom);

                // Map zones
                const zones: AnchorZoneDrawing[] = (data.zones || []).map((z: any, i: number) => ({
                    id: Date.now() + i,
                    nom: z.nom || `Zone ${i + 1}`,
                    anchor_text: z.anchor_text || '',
                    coords: z.coords || [0, 0, 0, 0],
                    anchor_offset: z.anchor_offset,
                    anchor_direction: z.anchor_direction || 'droite',
                    lang: z.lang || 'ara+fra',
                    char_filter: z.char_filter || 'none',
                    expected_format: z.expected_format || 'auto',
                    preprocess: z.preprocess || 'auto',
                    margin: z.margin || 0
                }));
                this.zones.set(zones);

                // Load image if available
                if (data.image_reference) {
                    // Extraire le chemin relatif au dossier 'uploads/'
                    const normalized = data.image_reference.replace(/\\/g, '/');
                    const uploadsIndex = normalized.indexOf('/uploads/');
                    let relativeFilename: string;
                    if (uploadsIndex !== -1) {
                        relativeFilename = normalized.substring(uploadsIndex + '/uploads/'.length);
                    } else {
                        relativeFilename = normalized.split('/').pop() || normalized;
                    }
                    const imageUrl = `http://localhost:8082/uploads/${relativeFilename}`;
                    this.imageUrl.set(imageUrl);
                    this.uploadedImageFilename.set(relativeFilename);
                    setTimeout(() => this.loadImageOnCanvas(imageUrl), 100);
                }

                this.isLoading.set(false);
                this.successMessage.set(`✏️ Édition de « ${nom} »`);
                setTimeout(() => this.successMessage.set(''), 3000);
            },
            error: (err) => {
                this.errorMessage.set('Erreur chargement entité: ' + (err.error?.message || err.message));
                this.isLoading.set(false);
            }
        });
    }

    supprimerEntite(nom: string) {
        if (!confirm(`Supprimer l'entité-ancre « ${nom} » ?`)) return;

        this.entityService.supprimerEntite(nom).subscribe({
            next: () => {
                this.successMessage.set(`🗑️ Entité « ${nom} » supprimée`);
                this.chargerEntites();
                setTimeout(() => this.successMessage.set(''), 3000);
            },
            error: (err) => {
                this.errorMessage.set('Erreur suppression: ' + (err.error?.message || err.message));
            }
        });
    }

    // ==================== SAUVEGARDE ====================

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

        // Vérifier que chaque zone a un anchor_text
        const missingAnchors = rawZones.filter(z => !z.anchor_text?.trim());
        if (missingAnchors.length > 0) {
            this.errorMessage.set(`⚠️ ${missingAnchors.length} zone(s) n'ont pas de texte ancre défini`);
            return;
        }

        // Strip UI helper props
        const processedZones: AnchorZone[] = rawZones.map(z => {
            const { valeurs_str, ...rest } = z;
            return rest;
        });

        this.isSaving.set(true);
        this.errorMessage.set('');
        this.successMessage.set('');

        this.entityService.sauvegarderEntiteAncre(
            name,
            processedZones,
            imageFilename,
            this.entityDescription()
        ).subscribe({
            next: () => {
                this.successMessage.set(`✅ Entité-ancre « ${name} » sauvegardée avec succès !`);
                this.isSaving.set(false);
                this.chargerEntites();
                setTimeout(() => this.reset(), 2000);
            },
            error: (err) => {
                this.errorMessage.set('Erreur sauvegarde: ' + (err.error?.message || err.message));
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
        this.editMode.set(false);
        this.editingEntityName.set('');
        this.errorMessage.set('');
        this.successMessage.set('');
    }
}
