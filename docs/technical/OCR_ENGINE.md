# ⚙️ Moteur OCR & Analyse Hybride

Ce document détaille le fonctionnement interne du moteur OCR (`ocr_engine.py`) d'EasyTess. Il explique comment le système combine plusieurs technologies pour garantir une extraction de données précise et robuste.

---

## 🏗️ Architecture

Le moteur utilise une approche **hybride** combinant plusieurs bibliothèques pour tirer profit de leurs forces respectives :

| Technologie | Usage Principal | Pourquoi ? |
|-------------|-----------------|------------|
| **Tesseract** | Analyse Globale & Zones simples | Rapide, bonne détection structurelle, standard industriel. |
| **EasyOCR** | Zones complexes, manuscrites, faible contraste | Plus lent mais beaucoup plus robuste (Deep Learning), supporte mieux les textes stylisés. |
| **ZBar (PyZbar)** | Codes-barres & QR Codes | Détection spécialisée et ultra-rapide des codes 1D/2D. |

---

## 📐 Système de Cadre de Référence (AABB)

Pour garantir que les zones d'extraction (Nom, Date, etc.) sont toujours localisées au bon endroit, même si l'image est décalée, scannée de travers ou redimensionnée, nous utilisons un **Cadre de Référence Dynamique**.

### Ancienne Méthode (Legacy)
Basée sur un point unique (Origine) et des dimensions fixes. Instable si l'échelle change (zoom/dézoom).

### Nouvelle Méthode : AABB (Axis-Aligned Bounding Box)
Le cadre est défini par **3 points d'ancrage** (étiquettes) :

1.  **HAUT (📍 Orange)** : Définit la limite supérieure (Y_min).
    *   *Exemple : "RÉPUBLIQUE ALGÉRIENNE"*
2.  **DROITE (📍 Bleu)** : Définit la limite droite (X_max).
    *   *Exemple : Logo ou Code MRZ "P<DZA"*
3.  **GAUCHE-BAS (📍 Vert)** : Définit le coin opposé (X_min, Y_max).
    *   *Exemple : "SIGNATURE" ou bas de photo.*

### Calcul du Cadre
Une fois ces 3 ancres détectées par OCR global :
- **X_min** = GAUCHE-BAS.x
- **Y_min** = HAUT.y
- **Largeur** = DROITE.x - GAUCHE-BAS.x
- **Hauteur** = GAUCHE-BAS.y - HAUT.y

Cela forme un rectangle précis qui "enferme" la zone utile du document.

> **Note :** La détection des ancres inclut une protection contre les "faux positifs" (ex: la lettre 'e' ne peut pas être confondue avec le mot 'Délivrance').

---

## ✂️ Pipeline d'Analyse (Physical Crop)

Pour assurer une fiabilité maximale ("Region of Interest" stricte), l'analyse suit ces étapes rigoureuses :

1.  **OCR Global** : Scan rapide de l'image entière pour trouver les 3 ancres.
2.  **Calcul du Cadre** : Détermination des coordonnées du cadre AABB en pixels.
3.  **Rognage Physique (Physical Crop)** :
    *   Le système crée une **copie temporaire** de l'image, coupée *exactement* aux bords du cadre.
    *   Tout le reste de l'image (bruit, bords de table, autres documents) est physiquement supprimé.
4.  **Analyse des Zones** :
    *   L'extraction (Tesseract/EasyOCR) se fait sur cette image rognée.
    *   Les coordonnées des zones sont relatives à ce crop.
5.  **Re-mapping des Coordonnées** :
    *   Une fois les textes extraits, les coordonnées des zones trouvées sont **reconverties** vers le repère de l'image originale.
    *   Cela permet à l'interface utilisateur d'afficher les résultats (rectangles bleus) exactement au bon endroit sur l'image source.

---

## 📊 Visualisation des résultats

Dans l'interface de test (`OCR Upload`) :

- **Avant Analyse (🟩 Vert)** : Affiche les zones telles qu'elles sont définies dans le modèle.
    *   *Position approximative (car le cadre n'est pas encore détecté).*
- **Après Analyse (🟦 Bleu)** : Affiche les zones réellement analysées.
    *   *Position exacte, alignée sur le document grâce au calcul du cadre.*

---

## 🛠️ Dépannage Technique

### "Pas de cadre de référence détecté"
Si les logs indiquent cette erreur, l'analyse bascule en mode "Image Complète" (fallback). Les zones risquent d'être décalées.
*   **Solution** : Vérifiez que l'entité possède bien les 3 ancres (Haut, Droite, Gauche-Bas) et qu'elles sont lisibles sur l'image.

### Zones affichées en haut à gauche (0,0)
Signifie que le re-mapping des coordonnées a échoué ou que le cadre n'a pas été trouvé.
*   **Solution** : Sauvegardez à nouveau l'entité avec la dernière version de l'éditeur pour mettre à jour ses métadonnées.
