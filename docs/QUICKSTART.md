# 🚀 Guide de Démarrage Rapide - EasyTess OCR

## 📋 Table des matières
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Fonctionnalités](#-fonctionnalités)
- [Documentation](#-documentation)

---

## 🔧 Installation

### Prérequis
- Python 3.8+
- Node.js 16+
- Tesseract OCR ([Télécharger](https://github.com/tesseract-ocr/tesseract))

### 1. Backend OCR

```bash
# S'il n'est pas déjà installé, installez le noyau commun en premier
cd backend/core_lib
pip install -e .

# Ensuite, installez l'environnement OCR et lancez l'API
cd ../app_ocr
pip install -r requirements.txt
python run.py
```

Le serveur démarre sur `http://localhost:8082`

### 2. Frontend OCR

```bash
cd frontend_ocr

# Installer les dépendances
npm install

# Lancer le serveur de développement
ng serve
```

L'application est accessible sur `http://localhost:4200`

---

## 🎯 Utilisation

### Analyser un document

1. **Ouvrir l'application** : `http://localhost:4100`
2. **Onglet "OCR Analysis"**
3. Sélectionner une entité (ou "Aucun" pour analyse libre)
4. Uploader une **image** ou un **PDF**
5. Cliquer sur **"Analyser avec OCR"**
6. Consulter les résultats
7. Exporter en JSON si nécessaire

### Créer une entité

1. **Onglet "Entity Management"**
2. Cliquer sur **"Créer une nouvelle entité"**
3. Nommer l'entité (ex: "CNI_Algérienne")
4. Uploader une image ou un PDF de référence
5. **Définir le Cadre de Référence** (3 points) :
   - Cliquer sur 📍 **Haut** (Orange) et dessiner sur un élément en haut (ex: "REPUBLIQUE").
   - Cliquer sur 📍 **Droite** (Bleu) et dessiner sur un élément à droite (ex: Logo/Code).
   - Cliquer sur 📍 **Gauche-Bas** (Vert) et dessiner sur un élément en bas à gauche.
6. **Dessiner les zones** d'extraction sur l'image
6. Pour chaque zone :
   - Nommer la zone
   - **Choisir le type** : 📝 Texte, 📦 QR Code, ou 🎫 Code-barres
7. Sauvegarder l'entité

### Utiliser une entité

1. **Onglet "OCR Analysis"**
2. Sélectionner l'entité créée
3. Uploader un document du même type
4. Analyser
5. Les zones sont automatiquement extraites !

---

## ✨ Fonctionnalités

### 📄 Formats supportés
- **Images** : JPG, PNG, BMP, TIFF, etc.
- **PDF** : Conversion automatique en image haute qualité

### 🔍 Types de zones
- **📝 Texte** : OCR avec Tesseract et EasyOCR
- **📦 QR Code** : Détection et décodage automatique
- **🎫 Code-barres** : Support avec zbar (optionnel)

### 🎨 Moteurs OCR
- **Tesseract** : Moteur principal (arabe + français)
- **EasyOCR** : Moteur de secours
- **OpenCV** : Détection de QR codes
- **pyzbar** : Détection de codes-barres (optionnel)

### 📊 Résultats
- Texte extrait par zone
- Contenu des QR codes décodés
- Niveau de confiance (0-100%)
- Moteur utilisé
- Export JSON

---

## 📚 Documentation

### Pour les utilisateurs
- **[README.md](../README.md)** - Documentation complète du projet
- **[GUIDE_PDF.md](./guides/GUIDE_PDF.md)** - Guide d'utilisation des PDF
- **[QRCODE_SUPPORT.md](./guides/QRCODE_SUPPORT.md)** - Guide QR Code et codes-barres
- **[DEMO_SCENARIOS.md](./guides/DEMO_SCENARIOS.md)** - Exemples pratiques

### Pour les développeurs
- **[PDF_SUPPORT.md](./technical/PDF_SUPPORT.md)** - Documentation technique PDF
- **[ZBAR_INSTALLATION.md](./technical/ZBAR_INSTALLATION.md)** - Installation de zbar
- **[CHANGELOG.md](./CHANGELOG.md)** - Historique des versions

---

## 🎬 Exemple rapide

### Scénario : Extraire des informations d'une facture PDF

#### 1. Créer l'entité "Facture"
```
1. Entity Management → Créer
2. Nom : "Facture_EDF"
3. Upload : facture_exemple.pdf
4. Dessiner zones :
   - "numero" (type: Texte)
   - "montant" (type: Texte)
   - "date" (type: Texte)
   - "qr_paiement" (type: QR Code)
5. Sauvegarder
```

#### 2. Analyser une nouvelle facture
```
1. OCR Analysis → Sélectionner "Facture_EDF"
2. Upload : nouvelle_facture.pdf
3. Analyser
4. Résultats automatiquement extraits !
```

#### 3. Résultat
```json
{
  "numero": "FAC-2026-001234",
  "montant": "156,78 €",
  "date": "03/01/2026",
  "qr_paiement": "PAYMENT-CODE-XYZ123"
}
```

---

## 🔧 Dépannage rapide

### Le serveur backend ne démarre pas
```bash
pip install -r requirements.txt
tesseract --version  # Vérifier Tesseract
```

### Erreur de conversion PDF
```bash
pip uninstall pypdfium2
pip install pypdfium2
```

### QR code non détecté
- Vérifier la qualité de l'image
- S'assurer que la zone couvre bien le QR code
- Essayer avec une résolution plus élevée

### Codes-barres non supportés
- Installer zbar (voir [ZBAR_INSTALLATION.md](./technical/ZBAR_INSTALLATION.md))
- Les QR codes fonctionnent sans zbar (OpenCV)

---

## 💡 Conseils

### Pour de meilleurs résultats OCR
- Utiliser des images nettes et bien contrastées
- Résolution minimale : 300 DPI
- Éviter les images floues ou mal éclairées
- Définir des zones précises
- **Texte arabe** : Le système filtre automatiquement les fonds texturés (passeports, CNI)

### Pour les QR codes
- Inclure tout le QR code dans la zone
- Laisser une petite marge autour
- Résolution minimale : 200x200 pixels pour le QR

### Pour les entités
- Utiliser des coordonnées relatives (automatique)
- Tester avec plusieurs documents du même type
- Nommer les zones de façon explicite

---

## 🎊 Prêt à commencer !

**Version actuelle** : 2.3.0  
**Statut** : ✅ Production Ready

Pour toute question, consultez la [documentation complète](../README.md) ou les [exemples pratiques](./guides/DEMO_SCENARIOS.md).

**Bon travail ! 🚀**
