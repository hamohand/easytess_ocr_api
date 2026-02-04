# Guide d'utilisation - Support PDF

## 🎯 Fonctionnalités disponibles

Votre application EasyTess supporte maintenant les fichiers PDF en plus des images ! Vous pouvez :
1. **Analyser des documents PDF** avec OCR
2. **Créer des entités** en utilisant un PDF comme modèle de référence

---

## 📋 Comment analyser un PDF avec OCR

### Étape 1 : Accéder à l'onglet "Analyse OCR"
- Ouvrez votre application Angular
- Cliquez sur l'onglet **"OCR Analysis"**

### Étape 2 : Sélectionner une entité (optionnel)
- Choisissez un modèle d'entité dans la liste déroulante
- Ou sélectionnez "Aucun" pour utiliser des zones par défaut

### Étape 3 : Uploader votre PDF
- Cliquez sur **"📁 Choisir une image ou un PDF"**
- Sélectionnez votre fichier PDF
- Cliquez sur **"⬆️ Uploader"**
- Le système convertit automatiquement la première page en image

### Étape 4 : Lancer l'analyse
- Une fois l'image affichée avec les zones, cliquez sur **"🔍 Analyser avec OCR"**
- Les résultats s'affichent dans un tableau avec :
  - Le texte détecté
  - Le niveau de confiance
  - Le moteur utilisé (Tesseract ou EasyOCR)
  - Le statut de détection

### Étape 5 : Exporter les résultats
- Cliquez sur **"💾 Exporter JSON"** pour télécharger les résultats

---

## 🏗️ Comment créer une entité avec un PDF

### Étape 1 : Accéder à la gestion des entités
- Ouvrez l'onglet **"Entity Management"**
- Cliquez sur **"➕ Créer une nouvelle entité"**

### Étape 2 : Nommer votre entité
- Entrez un nom descriptif (ex: "Passeport_France", "Facture_EDF")

### Étape 3 : Uploader votre PDF de référence
- Cliquez sur **"📁 Choisir une image ou un PDF"**
- Sélectionnez votre PDF modèle
- Le système le convertit automatiquement en image

### Étape 4 : Définir les zones d'extraction
Vous avez deux options :

**Option A : Dessiner à la souris**
- Cliquez et glissez sur l'image pour tracer un rectangle
- Relâchez pour créer la zone

**Option B : Ajouter manuellement**
- Cliquez sur **"➕ Ajouter une zone"**
- Déplacez et redimensionnez la zone sur le canvas

### Étape 5 : Nommer vos zones
- Dans le tableau des zones, modifiez les noms (ex: "Nom", "Prénom", "Date_naissance")

### Étape 6 : Sauvegarder
- Cliquez sur **"💾 Créer l'entité"**
- Votre modèle est maintenant disponible pour les analyses futures !

---

## ⚙️ Détails techniques

### Format de conversion
- **Résolution** : 300 DPI (haute qualité)
- **Format de sortie** : JPEG
- **Page convertie** : Première page uniquement

### Fichiers acceptés
- **Images** : JPG, PNG, BMP, TIFF, etc.
- **PDF** : Toutes versions

### Limitations
- Seule la **première page** du PDF est convertie
- Pour les PDF multi-pages, vous devrez les séparer au préalable

---

## 🔧 Dépannage

### Le PDF ne s'upload pas
- Vérifiez que le fichier n'est pas corrompu
- Assurez-vous que `pypdfium2` est installé : `pip install pypdfium2`

### L'image convertie est floue
- La résolution par défaut est 300 DPI
- Pour modifier, éditez `app/utils/pdf_utils.py` et changez le paramètre `dpi`

### Erreur "Erreur lors de la conversion PDF"
- Vérifiez les logs du serveur backend
- Le PDF pourrait être protégé ou corrompu

---

## 💡 Conseils d'utilisation

1. **Qualité du PDF** : Utilisez des PDF de bonne qualité pour de meilleurs résultats OCR
2. **Orientation** : Assurez-vous que le texte est dans le bon sens
3. **Zones précises** : Définissez des zones aussi précises que possible pour améliorer la détection
4. **Nommage** : Utilisez des noms de zones explicites pour faciliter l'exploitation des résultats

---

## 📞 Support

Pour toute question ou problème, consultez la documentation technique dans `PDF_SUPPORT.md`
