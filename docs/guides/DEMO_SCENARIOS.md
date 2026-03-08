# 🎬 Démonstration - Support PDF

## Scénario 1 : Analyser une facture PDF

### Contexte
Vous avez une facture au format PDF et vous souhaitez extraire automatiquement certaines informations (numéro de facture, montant, date, etc.).

### Étapes

#### 1️⃣ Créer l'entité "Facture"

**Dans l'interface Angular :**
```
1. Aller dans l'onglet "Entity Management"
2. Cliquer sur "➕ Créer une nouvelle entité"
3. Nommer l'entité : "Facture_EDF"
4. Cliquer sur "📁 Choisir une image ou un PDF"
5. Sélectionner une facture PDF type
6. Le système convertit automatiquement le PDF en image
```

**Définir les zones :**
```
7. Dessiner une zone autour du numéro de facture
   → Nommer : "numero_facture"
   
8. Dessiner une zone autour du montant TTC
   → Nommer : "montant_ttc"
   
9. Dessiner une zone autour de la date
   → Nommer : "date_facture"
   
10. Dessiner une zone autour du nom du client
    → Nommer : "nom_client"
```

**Sauvegarder :**
```
11. Cliquer sur "💾 Créer l'entité"
12. L'entité "Facture_EDF" est maintenant disponible
```

#### 2️⃣ Analyser une nouvelle facture

**Dans l'interface Angular :**
```
1. Aller dans l'onglet "OCR Analysis"
2. Sélectionner l'entité "Facture_EDF"
3. Cliquer sur "📁 Choisir une image ou un PDF"
4. Sélectionner une nouvelle facture PDF
5. Cliquer sur "⬆️ Uploader"
6. L'image convertie s'affiche avec les zones définies
7. Cliquer sur "🔍 Analyser avec OCR"
```

**Résultats :**
```
Zone              | Texte détecté        | Confiance | Moteur
------------------|---------------------|-----------|----------
numero_facture    | FAC-2025-001234     | 95%       | tesseract
montant_ttc       | 156,78 €            | 92%       | tesseract
date_facture      | 15/11/2025          | 88%       | tesseract
nom_client        | DUPONT Jean         | 91%       | tesseract
```

**Export :**
```
8. Cliquer sur "💾 Exporter JSON"
9. Fichier téléchargé : resultats_1733238456.json
```

---

## Scénario 2 : Traiter des CNI algériennes (PDF)

### Contexte
Vous recevez des copies de CNI algériennes scannées en PDF et vous devez extraire les informations d'identité.

### Étapes

#### 1️⃣ Créer l'entité "CNI_Algerie"

```
1. Entity Management → Créer une nouvelle entité
2. Nom : "CNI_Algerie_Recto"
3. Upload : cni_exemple.pdf
4. Conversion automatique en image
```

**Zones à définir :**
```
Zone 1 : "nom"           → Rectangle autour du nom de famille
Zone 2 : "prenom"        → Rectangle autour du prénom
Zone 3 : "date_naissance"→ Rectangle autour de la date de naissance
Zone 4 : "lieu_naissance"→ Rectangle autour du lieu de naissance
Zone 5 : "numero_cni"    → Rectangle autour du numéro de CNI
```

#### 2️⃣ Traiter plusieurs CNI

**Batch processing (manuel pour l'instant) :**
```
Pour chaque CNI PDF :
1. OCR Analysis → Sélectionner "CNI_Algerie_Recto"
2. Upload du PDF
3. Analyser
4. Exporter JSON
5. Répéter pour le suivant
```

**Résultat type :**
```json
{
  "filename": "cni_001.pdf",
  "date": "2025-12-03T17:30:00",
  "resultats": {
    "nom": {
      "texte_auto": "بن علي",
      "confiance_auto": 0.89,
      "moteur": "easyocr",
      "statut": "ok"
    },
    "prenom": {
      "texte_auto": "محمد",
      "confiance_auto": 0.92,
      "moteur": "easyocr",
      "statut": "ok"
    },
    "date_naissance": {
      "texte_auto": "15/03/1990",
      "confiance_auto": 0.95,
      "moteur": "tesseract",
      "statut": "ok"
    },
    "numero_cni": {
      "texte_auto": "123456789012",
      "confiance_auto": 0.97,
      "moteur": "tesseract",
      "statut": "ok"
    }
  }
}
```

---

## Scénario 3 : Extraire des données de contrats PDF

### Contexte
Vous avez des contrats de travail en PDF et vous devez extraire les informations clés.

### Étapes

#### 1️⃣ Créer l'entité "Contrat_Travail"

```
1. Nom : "Contrat_Travail"
2. Upload : contrat_type.pdf
3. Zones :
   - "nom_employe"
   - "poste"
   - "salaire"
   - "date_debut"
   - "duree_contrat"
   - "nom_employeur"
```

#### 2️⃣ Analyser les contrats

```
Pour chaque contrat :
1. Sélectionner l'entité "Contrat_Travail"
2. Upload du PDF
3. Analyser
4. Vérifier les résultats
5. Exporter
```

**Astuce :** Si certaines zones ont une faible confiance :
- Le système utilise automatiquement EasyOCR en secours
- Vérifiez visuellement les zones problématiques
- Ajustez les coordonnées des zones si nécessaire

---

## Scénario 4 : Formulaires administratifs

### Contexte
Traitement de formulaires administratifs standardisés en PDF.

### Avantages du PDF
- **Qualité** : Meilleure que les scans d'images
- **Texte vectoriel** : Conversion en haute résolution
- **Standardisation** : Format uniforme

### Workflow recommandé

```
1. Créer une entité par type de formulaire
2. Définir les zones une seule fois
3. Traiter tous les formulaires du même type
4. Exporter les résultats en JSON
5. Importer dans votre système de gestion
```

---

## 💡 Conseils pratiques

### Pour de meilleurs résultats

1. **Qualité du PDF**
   - Utilisez des PDF natifs plutôt que des scans
   - Résolution minimale : 150 DPI
   - Évitez les PDF protégés

2. **Définition des zones**
   - Soyez précis dans le tracé
   - Laissez une petite marge autour du texte
   - Évitez les zones qui se chevauchent

3. **Gestion des erreurs**
   - Vérifiez les alertes
   - Les zones avec confiance < 60% sont signalées
   - EasyOCR prend automatiquement le relais

4. **Performance**
   - La conversion PDF prend 1-2 secondes
   - L'analyse OCR prend 2-5 secondes par zone
   - Utilisez des entités pour éviter de redéfinir les zones

### Limitations à connaître

1. **Une seule page**
   - Seule la première page est convertie
   - Pour les PDF multi-pages, séparez-les d'abord

2. **Texte uniquement**
   - Les images dans le PDF sont converties en pixels
   - Pas de reconnaissance de tableaux complexes

3. **Langues**
   - Arabe et Français par défaut
   - Pour d'autres langues, modifier la configuration

---

## 📊 Cas d'usage réels

### ✅ Adapté pour :
- Factures standardisées
- Documents d'identité
- Formulaires administratifs
- Contrats types
- Bulletins de paie
- Attestations

### ⚠️ Moins adapté pour :
- PDF multi-pages complexes
- Documents avec mise en page variable
- PDF avec beaucoup d'images
- Documents manuscrits scannés

---

## 🎯 Résultats attendus

### Taux de réussite typique
- **Documents imprimés** : 90-95% de confiance
- **Texte arabe** : 85-92% avec EasyOCR
- **Texte français** : 92-97% avec Tesseract
- **Chiffres** : 95-98% de confiance

### Temps de traitement
- **Upload + conversion** : 2-3 secondes
- **Analyse OCR** : 3-5 secondes (4 zones)
- **Total** : ~8 secondes par document

---

**Prêt à tester ?** 🚀

Suivez les scénarios ci-dessus avec vos propres documents PDF !
