# 🔧 Installation de zbar sur Windows - Solutions alternatives

## ❌ Problème
Le fichier `libzbar-64.dll` n'est pas facilement trouvable sur SourceForge.

## ✅ Solutions alternatives

---

## Solution 1 : Utiliser le package pyzbar avec DLL incluse (RECOMMANDÉ)

### Téléchargement direct de la DLL

**Lien direct :**
https://github.com/NaturalHistoryMuseum/pyzbar/releases

Ou utilisez cette commande PowerShell pour télécharger automatiquement :

```powershell
# Créer un dossier pour la DLL
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\zbar"

# Télécharger la DLL (64-bit)
Invoke-WebRequest -Uri "https://github.com/NaturalHistoryMuseum/pyzbar/raw/master/pyzbar/libzbar-64.dll" -OutFile "$env:USERPROFILE\zbar\libzbar-64.dll"

# Copier dans System32
Copy-Item "$env:USERPROFILE\zbar\libzbar-64.dll" -Destination "C:\Windows\System32\" -Force
```

---

## Solution 2 : Installer via pip avec les binaires

Certaines versions de pyzbar incluent déjà les DLL :

```bash
pip uninstall pyzbar
pip install pyzbar[scripts]
```

Ou essayez cette version spécifique :

```bash
pip install pyzbar==0.1.9
```

---

## Solution 3 : Téléchargement manuel depuis GitHub

### Étapes :

1. **Télécharger le fichier DLL** :
   - Aller sur : https://github.com/NaturalHistoryMuseum/pyzbar
   - Naviguer vers : `pyzbar/libzbar-64.dll`
   - Cliquer sur "Download" ou "Raw"

2. **Placer la DLL** :
   ```
   C:\Windows\System32\libzbar-64.dll
   ```

3. **Ou dans le dossier du projet** :
   ```
   easytess-backend\libzbar-64.dll
   ```

---

## Solution 4 : Utiliser OpenCV uniquement (SANS pyzbar)

Si vous ne parvenez pas à installer zbar, vous pouvez utiliser **uniquement OpenCV** pour les QR codes (pas les codes-barres) :

### Modifier le code

Dans `app/utils/qrcode_utils.py`, la fonction `decoder_code_hybride()` utilise déjà OpenCV en fallback !

**Test :**
```python
from app.utils.qrcode_utils import decoder_qrcode_opencv

# Tester avec OpenCV uniquement
result = decoder_qrcode_opencv('path/to/image.jpg', [100, 100, 300, 300])
print(result)
```

**Avantages :**
- ✅ Pas besoin de zbar DLL
- ✅ OpenCV déjà installé dans votre projet
- ✅ Fonctionne pour les QR codes

**Inconvénients :**
- ❌ Ne supporte QUE les QR codes (pas les codes-barres)

---

## Solution 5 : Script PowerShell automatique

Créez un fichier `install_zbar.ps1` :

```powershell
# install_zbar.ps1
Write-Host "Installation de zbar pour pyzbar..." -ForegroundColor Green

# URL de la DLL
$dllUrl = "https://raw.githubusercontent.com/NaturalHistoryMuseum/pyzbar/master/pyzbar/libzbar-64.dll"
$tempPath = "$env:TEMP\libzbar-64.dll"
$destPath = "C:\Windows\System32\libzbar-64.dll"

try {
    # Télécharger
    Write-Host "Téléchargement de libzbar-64.dll..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $dllUrl -OutFile $tempPath
    
    # Copier (nécessite admin)
    Write-Host "Installation dans System32..." -ForegroundColor Yellow
    Copy-Item $tempPath -Destination $destPath -Force
    
    Write-Host "✅ Installation réussie !" -ForegroundColor Green
    Write-Host "DLL installée : $destPath" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Erreur : $_" -ForegroundColor Red
    Write-Host "Essayez de lancer PowerShell en tant qu'administrateur" -ForegroundColor Yellow
}
```

**Exécuter :**
```powershell
# En tant qu'administrateur
powershell -ExecutionPolicy Bypass -File install_zbar.ps1
```

---

## Solution 6 : Placer la DLL dans le dossier du projet

Si vous ne pouvez pas copier dans System32, placez la DLL directement dans votre projet :

```
easytess-backend/
├── app/
├── libzbar-64.dll  ← Ici
├── run.py
└── requirements.txt
```

Puis ajoutez ce code au début de `app/utils/qrcode_utils.py` :

```python
import os
import sys

# Ajouter le dossier du projet au PATH pour trouver la DLL
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in os.environ['PATH']:
    os.environ['PATH'] = project_root + os.pathsep + os.environ['PATH']
```

---

## 🧪 Tester l'installation

### Test 1 : Vérifier si pyzbar trouve la DLL

```python
try:
    from pyzbar import pyzbar
    print("✅ pyzbar importé avec succès")
    
    # Tester avec une image
    from PIL import Image
    import numpy as np
    
    # Créer une image de test (vide)
    img = Image.new('RGB', (100, 100), color='white')
    result = pyzbar.decode(np.array(img))
    print("✅ pyzbar fonctionne (aucun code détecté dans l'image vide, c'est normal)")
    
except Exception as e:
    print(f"❌ Erreur : {e}")
    print("\nSolutions :")
    print("1. Installer la DLL zbar (voir ci-dessus)")
    print("2. Ou utiliser OpenCV uniquement (QR codes seulement)")
```

### Test 2 : Tester avec OpenCV (fallback)

```python
from app.utils.qrcode_utils import decoder_qrcode_opencv

print("Test avec OpenCV (pas besoin de zbar) :")
# Créer une image de test
result = decoder_qrcode_opencv('path/to/qrcode_image.jpg')
print(result)
```

---

## 🎯 Recommandation

### Option A : Vous voulez QR codes + codes-barres
→ Utilisez **Solution 1** (téléchargement direct GitHub)

### Option B : Vous voulez UNIQUEMENT des QR codes
→ Utilisez **Solution 4** (OpenCV uniquement, déjà installé)

### Option C : Vous avez des droits admin
→ Utilisez **Solution 5** (script PowerShell automatique)

---

## 📝 Commandes rapides

### Télécharger la DLL manuellement (PowerShell) :

```powershell
# Télécharger
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/NaturalHistoryMuseum/pyzbar/master/pyzbar/libzbar-64.dll" -OutFile "libzbar-64.dll"

# Copier dans System32 (nécessite admin)
Copy-Item "libzbar-64.dll" -Destination "C:\Windows\System32\" -Force
```

### Ou placer dans le projet :

```powershell
# Télécharger dans le dossier backend
cd easytess-backend
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/NaturalHistoryMuseum/pyzbar/master/pyzbar/libzbar-64.dll" -OutFile "libzbar-64.dll"
```

---

## ✅ Alternative : Utiliser UNIQUEMENT OpenCV

Si l'installation de zbar est trop compliquée, votre système **fonctionne déjà** avec OpenCV pour les QR codes !

**Modifier `app/services/ocr_engine.py` :**

Remplacer :
```python
from app.utils.qrcode_utils import decoder_code_hybride
```

Par :
```python
from app.utils.qrcode_utils import decoder_qrcode_opencv as decoder_code_hybride
```

**Avantages :**
- ✅ Pas besoin de DLL
- ✅ Fonctionne immédiatement
- ✅ Supporte les QR codes

**Inconvénient :**
- ❌ Ne supporte pas les codes-barres (EAN, Code128, etc.)

---

## 🆘 Si rien ne fonctionne

Contactez-moi avec le message d'erreur exact que vous obtenez :

```python
try:
    from pyzbar import pyzbar
    print("OK")
except Exception as e:
    print(f"Erreur : {e}")
```

Et je vous aiderai à trouver une solution adaptée à votre configuration !

---

**Fichier créé : ZBAR_INSTALLATION.md**
