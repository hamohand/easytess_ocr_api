import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EntityService } from '../../services/entity.service';

interface MappingItem {
  destinationZone: string;
  sourceEntity: string;
  sourceZone: string;
}

@Component({
  selector: 'app-composite-creator',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './composite-creator.component.html',
  styleUrls: ['./composite-creator.component.css']
})
export class CompositeCreatorComponent implements OnInit {
  private entityService = inject(EntityService);

  composites = signal<any[]>([]);
  entities = signal<any[]>([]);

  // Formulaire création
  compositeName = signal('');
  compositeDescription = signal('');
  
  // Selection des entités
  selectedEntities = signal<{nom: string, label: string}[]>([]); // ex: {nom: 'cni_recto', label: 'Recto'}
  availableEntities = signal<any[]>([]);

  // Mapping
  mappings = signal<MappingItem[]>([]);
  
  // New mapping row
  newDestZone = signal('');
  newSrcEntity = signal('');
  newSrcZone = signal('');
  
  message = signal<{text: string, isError: boolean} | null>(null);
  
  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.entityService.listerEntites().subscribe({
      next: (data) => {
        this.entities.set(data);
        this.availableEntities.set(data);
      }
    });
    this.entityService.listerComposites().subscribe({
      next: (data) => this.composites.set(data)
    });
  }

  addEntity(entityName: string) {
    if (!entityName) return;
    const current = this.selectedEntities();
    if (!current.find(e => e.nom === entityName)) {
      this.selectedEntities.set([...current, {nom: entityName, label: `Partie ${current.length + 1}`}]);
    }
  }

  removeEntity(entityName: string) {
    this.selectedEntities.set(this.selectedEntities().filter(e => e.nom !== entityName));
    // Remove bindings
    this.mappings.set(this.mappings().filter(m => m.sourceEntity !== entityName));
  }

  addMapping() {
    if (!this.newDestZone() || !this.newSrcEntity() || !this.newSrcZone()) {
      this.showMessage('Veuillez remplir tous les champs du mapping', true);
      return;
    }
    
    this.mappings.update(m => [...m, {
      destinationZone: this.newDestZone(),
      sourceEntity: this.newSrcEntity(),
      sourceZone: this.newSrcZone()
    }]);
    
    this.newDestZone.set('');
    this.newSrcZone.set('');
  }

  removeMapping(index: number) {
    this.mappings.update(m => m.filter((_, i) => i !== index));
  }

  getZonesForEntity(entityName: string): any[] {
    const ent = this.entities().find(e => e.nom === entityName);
    return ent ? ent.zones : [];
  }

  saveComposite() {
    if (!this.compositeName() || this.selectedEntities().length < 2) {
      this.showMessage('Veuillez saisir un nom et sélectionner au moins 2 entités.', true);
      return;
    }

    const mappingObj: any = {};
    for (const m of this.mappings()) {
      mappingObj[m.destinationZone] = {
        entite: m.sourceEntity,
        zone: m.sourceZone
      };
    }

    const sous_entites = this.selectedEntities().map(e => e.nom);

    this.entityService.sauvegarderComposite(
      this.compositeName(),
      sous_entites,
      mappingObj,
      this.compositeDescription()
    ).subscribe({
      next: () => {
        this.showMessage('Entité composite sauvegardée avec succès !', false);
        this.loadData();
        this.resetForm();
      },
      error: (err) => this.showMessage(`Erreur: ${err.error?.error || err.message}`, true)
    });
  }

  resetForm() {
    this.compositeName.set('');
    this.compositeDescription.set('');
    this.selectedEntities.set([]);
    this.mappings.set([]);
  }

  showMessage(text: string, isError: boolean) {
    this.message.set({text, isError});
    setTimeout(() => this.message.set(null), 4000);
  }
}
