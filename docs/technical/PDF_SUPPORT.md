# Support PDF pour l'analyse OCR et la création d'entités

## Fonctionnalités ajoutées

### 1. Analyse OCR sur PDF
- Les utilisateurs peuvent maintenant uploader des fichiers PDF pour l'analyse OCR
- Le backend convertit automatiquement la première page du PDF en image JPEG haute qualité (300 DPI)
- L'analyse OCR se fait ensuite sur l'image convertie

### 2. Création d'entités sur PDF
- Les utilisateurs peuvent uploader un PDF comme image de référence lors de la création d'entités
- Le PDF est automatiquement converti en image
- Les zones peuvent être définies sur l'image convertie comme pour une image normale

## Modifications techniques

### Backend

#### 1. Nouvelle dépendance
- Ajout de `pypdfium2` dans `requirements.txt`
- Bibliothèque légère et performante pour le rendu PDF

#### 2. Nouveau module utilitaire
**Fichier**: `app/utils/pdf_utils.py`
- Fonction `convert_pdf_to_image(pdf_path, output_path, dpi=300)`
- Convertit la première page d'un PDF en image JPEG
- Résolution par défaut: 300 DPI pour une qualité optimale

#### 3. Routes modifiées

**`app/api/file_routes.py`** - Route `/api/upload`
- Détection automatique des fichiers PDF
- Conversion en image avant traitement
- L'image convertie remplace le PDF pour le reste du workflow

**`app/api/entity_routes.py`** - Route `/api/upload-image-entite`
- Même logique de conversion pour les uploads d'entités
- Gestion des erreurs de conversion

### Frontend

#### 1. Composant d'analyse OCR
**Fichier**: `ocr-upload.component.html`
- Input file accepte maintenant `image/*,.pdf`
- Label mis à jour: "Choisir une image ou un PDF"

**Fichier**: `ocr-upload.component.ts`
- Détection du type de fichier (PDF vs image)
- Pas de prévisualisation locale pour les PDF
- La prévisualisation se fait après upload et conversion côté serveur

#### 2. Composant de création d'entités
**Fichier**: `entity-creator.component.html`
- Input file accepte maintenant `image/*,.pdf`
- Label mis à jour: "Choisir une image ou un PDF"

**Fichier**: `entity-creator.component.ts`
- Pas de modification nécessaire
- Le backend gère la conversion de manière transparente

## Flux de traitement

### Pour l'analyse OCR
1. Utilisateur sélectionne un PDF
2. Frontend détecte le type PDF et désactive la prévisualisation locale
3. Upload vers `/api/upload`
4. Backend convertit le PDF en JPEG
5. Backend retourne l'URL de l'image convertie
6. Frontend affiche l'image convertie avec les zones
7. Analyse OCR sur l'image convertie

### Pour la création d'entités
1. Utilisateur sélectionne un PDF comme image de référence
2. Upload vers `/api/upload-image-entite`
3. Backend convertit le PDF en JPEG
4. Backend retourne l'URL de l'image convertie avec dimensions
5. Frontend charge l'image sur le canvas
6. Utilisateur définit les zones sur l'image
7. Sauvegarde de l'entité avec l'image convertie

## Limitations actuelles
- Seule la première page du PDF est convertie
- Format de sortie fixé à JPEG
- Résolution fixée à 300 DPI

## Améliorations futures possibles
- Support multi-pages (conversion de toutes les pages)
- Choix de la page à convertir
- Paramétrage de la résolution
- Support d'autres formats de sortie (PNG, TIFF)
