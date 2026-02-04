// entity-creator.component.ts
import { Component, signal, inject, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../entity.service';
import { Zone } from '../models';

interface ZoneDrawing extends Zone {
    id: number;
    valeurs_str?: string; // Pour le binding l'input (comma separated)
}

@Component({
    selector: 'app-entity-creator',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './entity-creator.component.html',
    styleUrls: ['./entity-creator.component.css']
})
export class EntityCreatorComponent implements AfterViewInit {
    private entityService = inject(EntityService);

    @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
    @ViewChild('imageInput') imageInputRef!: ElementRef<HTMLInputElement>;

    // Signals
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

    // Canvas state
    private ctx: CanvasRenderingContext2D | null = null;
    private img: HTMLImageElement | null = null;
    private startX = 0;
    private startY = 0;
    private currentRect: { x: number; y: number; width: number; height: number } | null = null;

    ngAfterViewInit() {
        const canvas = this.canvasRef.nativeElement;
        this.ctx = canvas.getContext('2d');
    }

    onImageSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            const file = input.files[0];
            this.uploadImage(file);
        }
    }

    uploadImage(file: File) {
        this.errorMessage.set('');
        this.entityService.uploadImageEntite(file).subscribe({
            next: (response) => {
                this.uploadedImageFilename.set(response.filename);
                this.imageUrl.set(response.image_url);
                this.loadImageOnCanvas(response.image_url);
                console.log('✅ Image uploadée:', response.filename);
            },
            error: (err) => {
                this.errorMessage.set('Erreur upload: ' + err.message);
            }
        });
    }

    loadImageOnCanvas(url: string) {
        const img = new Image();
        img.onload = () => {
            this.img = img;
            const canvas = this.canvasRef.nativeElement;

            // Resize canvas to fit image
            const maxWidth = 800;
            const scale = Math.min(1, maxWidth / img.width);
            canvas.width = img.width * scale;
            canvas.height = img.height * scale;

            this.redrawCanvas();
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

        // Only add zone if it has a minimum size
        if (this.currentRect.width > 10 && this.currentRect.height > 10) {
            const zoneName = this.currentZoneName() || `Zone ${this.zones().length + 1}`;

            const zone: ZoneDrawing = {
                id: Date.now(),
                nom: zoneName,
                type: 'text', // Default type
                valeurs_str: '', // Init flat values
                coords: [
                    Math.round(this.currentRect.x),
                    Math.round(this.currentRect.y),
                    Math.round(this.currentRect.x + this.currentRect.width),
                    Math.round(this.currentRect.y + this.currentRect.height)
                ]
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

        // Draw existing zones
        this.zones().forEach((zone, index) => {
            const [x1, y1, x2, y2] = zone.coords;
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
        const processedZones: Zone[] = rawZones.map(z => {
            const { valeurs_str, ...rest } = z; // Remove UI helper props
            const zone: Zone = { ...rest };

            if (valeurs_str && z.type === 'text') {
                zone.valeurs_attendues = valeurs_str.split(',')
                    .map(v => v.trim())
                    .filter(v => v.length > 0);
            }
            return zone;
        });

        this.isSaving.set(true);
        this.errorMessage.set('');
        this.successMessage.set('');

        this.entityService.sauvegarderEntite(
            name,
            processedZones,
            imageFilename,
            this.entityDescription()
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
        this.currentZoneName.set('');
        this.successMessage.set('');
        this.errorMessage.set('');

        if (this.ctx && this.canvasRef) {
            const canvas = this.canvasRef.nativeElement;
            this.ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    }
}
