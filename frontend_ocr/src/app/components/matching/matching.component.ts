import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../../services/entity.service';
import { OcrService } from '../../services/ocr.service';
import { FileService } from '../../services/file.service';

export interface MatchingDataResult {
  texte_final?: string | null;
  texte_auto?: string | null;
  statut?: string | null;
  confiance_auto?: number | null;
  [key: string]: any;
}

export interface MatchingResult {
  nom_composite: string;
  date_fusion: Date;
  donnees: Record<string, MatchingDataResult>;
}

@Component({
  selector: 'app-matching',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './matching.component.html',
  styleUrls: ['./matching.component.css']
})
export class MatchingComponent implements OnInit {
  private entityService = inject(EntityService);
  private ocrService = inject(OcrService);
  private fileService = inject(FileService);

  composites = signal<any[]>([]);
  selectedComposite = signal<any | null>(null);

  // Pour chaque face attendue, on stocke le fichier uploadé ou l'ID de session etc.
  // {[nomEntite: string]: { file?: File, previewUrl?: string, analyseResult?: any, isAnalyzing: boolean }}
  faceInputs = signal<Record<string, any>>({});
  
  // Résultat fusionné
  finalResult = signal<MatchingResult | null>(null);
  
  message = signal<{text: string, isError: boolean} | null>(null);
  globalAnalyzing = signal(false);

  ngOnInit() {
    this.entityService.listerComposites().subscribe({
      next: (data) => this.composites.set(data)
    });
  }

  onCompositeChange(nom: string) {
    if (!nom) {
      this.selectedComposite.set(null);
      this.faceInputs.set({});
      return;
    }
    const c = this.composites().find(x => x.nom === nom);
    this.selectedComposite.set(c);
    
    // Initialiser les faceInputs
    const inputs: any = {};
    for (const sub of c.sous_entites) {
      inputs[sub] = { file: null, previewUrl: null, analyseResult: null, isAnalyzing: false };
    }
    this.faceInputs.set(inputs);
    this.finalResult.set(null);
  }

  onFileSelected(event: Event, entiteFace: string) {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        const url = e.target?.result as string;
        this.faceInputs.update(fi => {
          const newFi = { ...fi };
          newFi[entiteFace] = { ...newFi[entiteFace], file: file, previewUrl: url };
          return newFi;
        });
      };
      reader.readAsDataURL(file);
    }
  }

  // Effectue l'OCR sur une face spécifique
  analyserFace(entiteFace: string) {
    const input = this.faceInputs()[entiteFace];
    if (!input || !input.file) return;

    this.faceInputs.update(fi => ({...fi, [entiteFace]: {...fi[entiteFace], isAnalyzing: true}}));

    this.fileService.uploadImage(input.file).subscribe({
      next: (uploadRes) => {
        // Appeler backend pour analyser avec entiteFace
        // Note: Ici il faudrait récupérer la configuration de la face et l'envoyer à analyserImage
        this.entityService.getEntite(entiteFace).subscribe({
            next: (entite) => {
                const zonesConfig: any = {};
                if (entite.zones) {
                    entite.zones.forEach((z:any) => {
                        zonesConfig[z.nom] = { coords: z.coords };
                    });
                }
                
                this.ocrService.analyserImage(uploadRes.saved_filename, zonesConfig, entite.cadre_reference).subscribe({
                  next: (analyseRes) => {
                    this.faceInputs.update(fi => ({...fi, [entiteFace]: {...fi[entiteFace], isAnalyzing: false, analyseResult: analyseRes}}));
                    this.checkAutoMatch();
                  },
                  error: (err) => {
                    this.faceInputs.update(fi => ({...fi, [entiteFace]: {...fi[entiteFace], isAnalyzing: false}}));
                    this.showMessage(`Erreur analyse OCR pour ${entiteFace}`, true);
                  }
                });
            }
        });
      },
      error: (err) => {
        this.faceInputs.update(fi => ({...fi, [entiteFace]: {...fi[entiteFace], isAnalyzing: false}}));
        this.showMessage(`Erreur upload pour ${entiteFace}`, true);
      }
    });
  }
  
  analyserTout() {
    // Lance l'analyse de toutes les faces qui ont un fichier mais pas encore de résultat
    const inputs = this.faceInputs();
    for (const face of Object.keys(inputs)) {
      if (inputs[face].file && !inputs[face].analyseResult) {
        this.analyserFace(face);
      }
    }
  }

  checkAutoMatch() {
    // Vérifie si toutes les faces ont été analysées, si oui, fusionner !
    const c = this.selectedComposite();
    if (!c) return;
    
    const inputs = this.faceInputs();
    
    // S'il manque un résultat OCR pour une des faces, on attend
    for (const sub of c.sous_entites) {
      if (!inputs[sub].analyseResult) return;
    }
    
    // Tout est là, on fusionne !
    this.effectuerAppariement(c, inputs);
  }

  effectuerAppariement(composite: any, inputs: any) {
    const resultatMappee: any = {};
    
    // Mapping: { destination: { entite: "...", zone: "..." } }
    for (const destAttr of Object.keys(composite.mapping)) {
      const src = composite.mapping[destAttr];
      const faceResult = inputs[src.entite]?.analyseResult?.resultats;
      
      if (faceResult && faceResult[src.zone]) {
        resultatMappee[destAttr] = faceResult[src.zone];
      } else {
        resultatMappee[destAttr] = { texte_auto: null, statut: "non trouvé" };
      }
    }
    
    this.finalResult.set({
      nom_composite: composite.nom,
      date_fusion: new Date(),
      donnees: resultatMappee
    });
    
    this.showMessage("Appariement réussi ! Document final généré.", false);
  }

  exportResult() {
    const data = this.finalResult();
    if (!data) return;
    
    this.fileService.downloadJsonFile(data).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${data.nom_composite}_${Date.now()}.json`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    });
  }

  showMessage(text: string, isError: boolean) {
    this.message.set({text, isError});
    setTimeout(() => this.message.set(null), 4000);
  }
}
