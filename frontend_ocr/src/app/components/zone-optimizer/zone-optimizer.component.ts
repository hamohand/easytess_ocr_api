import { Component, OnInit, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../../services/entity.service';
import { OptimizerService, OptimizerResult, OptimizerRequest } from '../../services/optimizer.service';
import { Entite, Zone } from '../../services/models';

@Component({
  selector: 'app-zone-optimizer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './zone-optimizer.component.html',
  styleUrls: ['./zone-optimizer.component.css']
})
export class ZoneOptimizerComponent implements OnInit, OnChanges {
  @Input() defaultEntityName: string = '';

  entities: Entite[] = [];
  selectedEntityName: string = '';
  selectedEntity: Entite | null = null;
  
  availableZones: Zone[] = [];
  selectedZoneName: string = '';
  selectedZone: Zone | null = null;
  
  texteAttendu: string = '';
  stopThreshold: number | null = null;
  
  
  isOptimizing: boolean = false;
  optimizationComplete: boolean = false;
  optimizationResult: OptimizerResult | null = null;
  
  errorMsg: string = '';
  successMsg: string = '';

  constructor(
      private entityService: EntityService,
      private optimizerService: OptimizerService
  ) {}

  ngOnInit() {
      this.loadEntities();
  }

  ngOnChanges(changes: SimpleChanges) {
      if (changes['defaultEntityName'] && this.defaultEntityName) {
          this.selectedEntityName = this.defaultEntityName;
          if (this.entities.length > 0) {
              this.onEntitySelect();
          }
      }
  }

  loadEntities() {
      this.entityService.listerEntites().subscribe({
          next: (data) => {
              this.entities = data;
              if (this.defaultEntityName) {
                  this.selectedEntityName = this.defaultEntityName;
                  this.onEntitySelect();
              }
          },
          error: (err) => {
              this.errorMsg = 'Erreur lors du chargement des entités.';
          }
      });
  }

  onEntitySelect() {
      this.selectedEntity = this.entities.find(e => e.nom === this.selectedEntityName) || null;
      this.availableZones = this.selectedEntity?.zones || [];
      // Only reset zone if not found in new entity
      if (!this.availableZones.find(z => z.nom === this.selectedZoneName)) {
          this.selectedZoneName = '';
          this.selectedZone = null;
      }
      this.resetOptimization();
  }

  onZoneSelect() {
      this.selectedZone = this.availableZones.find(z => z.nom === this.selectedZoneName) || null;
      this.resetOptimization();
  }

  resetOptimization() {
      this.isOptimizing = false;
      this.optimizationComplete = false;
      this.optimizationResult = null;
      this.errorMsg = '';
      this.successMsg = '';
  }

  runOptimization() {
      if (!this.selectedEntityName || !this.selectedZoneName || !this.texteAttendu) {
          this.errorMsg = 'Veuillez remplir tous les champs.';
          return;
      }

      this.resetOptimization();
      this.isOptimizing = true;

      const request: OptimizerRequest = {
          entity_name: this.selectedEntityName,
          zone_name: this.selectedZoneName,
          texte_attendu: this.texteAttendu,
          use_tesseract: true,
          use_easyocr: false
      };

      if (this.stopThreshold !== null && this.stopThreshold > 0) {
          request.stop_threshold = this.stopThreshold;
      }

      this.optimizerService.runOptimization(request).subscribe({
          next: (res) => {
              this.optimizationResult = res;
              this.optimizationComplete = true;
              this.isOptimizing = false;
          },
          error: (err) => {
              this.errorMsg = "L'optimisation a échoué: " + (err.error?.error || err.message);
              this.isOptimizing = false;
          }
      });
  }

  applyOptimalCoordinates() {
      if (!this.optimizationResult || !this.selectedEntityName || !this.selectedZone) {
          return;
      }
      
      const optimalCoords = this.optimizationResult.optimal.coords;
      const newZone = { 
          ...this.selectedZone, 
          coords: [optimalCoords[0], optimalCoords[1], optimalCoords[2], optimalCoords[3]] as [number, number, number, number] 
      };
      
      this.entityService.modifierZone(this.selectedEntityName, this.selectedZone.id!, newZone).subscribe({
          next: () => {
              this.successMsg = 'Coordonnées appliquées avec succès !';
              // Update local state so it matches the newly applied coords
              this.selectedZone!.coords = newZone.coords;
          },
          error: (err) => {
              this.errorMsg = "Erreur lors de l'application: " + (err.error?.error || err.message);
          }
      });
  }
}
