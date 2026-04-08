# 📦 Guide d'Installation Rapide - EasyTess Frontend

## 🎯 Structure actuelle

```
angular-services/
├── services/              # ← Services API (à copier dans votre projet)
│   ├── models.ts
│   ├── ocr.service.ts
│   ├── entity.service.ts
│   ├── file.service.ts
│   └── index.ts
├── components/            # ← Composants Angular (à copier dans votre projet)
│   ├── ocr-upload.component.ts
│   ├── ocr-upload.component.html
│   ├── ocr-upload.component.css
│   ├── entity-creator.component.ts
│   ├── entity-creator.component.html
│   └── entity-creator.component.css
└── example-app/           # ← Exemple d'application (fichiers de configuration)
    ├── app.component.ts
    ├── app.component.html
    ├── app.component.css
    ├── app.config.ts
    ├── main.ts
    ├── index.html
    ├── styles.css
    ├── package.json
    └── tsconfig.json
```

## 🚀 Installation - Méthode Rapide

### Étape 1 : Créer un nouveau projet Angular

```bash
# Installer Angular CLI si nécessaire
npm install -g @angular/cli

# Créer un nouveau projet
ng new frontend_ocr --standalone --routing=false --style=css
cd frontend_ocr
```

### Étape 2 : Copier les fichiers

**Depuis le dossier `angular-services/`, copiez :**

1. **Services** → `src/app/services/`
   ```
   Copier tout le dossier angular-services/services/
   vers frontend_ocr/src/app/services/
   ```

2. **Composants** → `src/app/components/`
   ```
   Copier tout le dossier angular-services/components/
   vers frontend_ocr/src/app/components/
   ```

3. **Fichiers d'application** (depuis `example-app/`) :
   - `app.component.ts` → `src/app/app.component.ts` (REMPLACER)
   - `app.component.html` → `src/app/app.component.html` (REMPLACER)
   - `app.component.css` → `src/app/app.component.css` (REMPLACER)
   - `app.config.ts` → `src/app/app.config.ts` (REMPLACER)
   - `main.ts` → `src/main.ts` (REMPLACER)
   - `index.html` → `src/index.html` (REMPLACER)
   - `styles.css` → `src/styles.css` (REMPLACER)

### Étape 3 : Ajuster les imports dans app.component.ts

Après avoir copié les fichiers, `src/app/app.component.ts` devrait avoir :

```typescript
import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OcrUploadComponent } from './components/ocr-upload.component';
import { EntityCreatorComponent } from './components/entity-creator.component';
```

### Étape 4 : Installer et lancer

```bash
npm install
ng serve
```

Ouvrez `http://localhost:4100`

## 📁 Structure finale du projet

```
frontend_ocr/
├── src/
│   ├── main.ts
│   ├── index.html
│   ├── styles.css
│   └── app/
│       ├── app.config.ts
│       ├── app.component.ts
│       ├── app.component.html
│       ├── app.component.css
│       ├── services/              # ← Copié depuis angular-services/services/
│       │   ├── models.ts
│       │   ├── ocr.service.ts
│       │   ├── entity.service.ts
│       │   ├── file.service.ts
│       │   └── index.ts
│       └── components/            # ← Copié depuis angular-services/components/
│           ├── ocr-upload.component.ts
│           ├── ocr-upload.component.html
│           ├── ocr-upload.component.css
│           ├── entity-creator.component.ts
│           ├── entity-creator.component.html
│           └── entity-creator.component.css
├── package.json
├── tsconfig.json
└── angular.json (généré par ng new)
```

## ⚡ Alternative : Script de copie automatique

Créez un fichier `setup.bat` (Windows) :

```batch
@echo off
echo Création du projet Angular...
call ng new frontend_ocr --standalone --routing=false --style=css --skip-git

echo Copie des services...
xcopy /E /I angular-services\services frontend_ocr\src\app\services

echo Copie des composants...
xcopy /E /I angular-services\components frontend_ocr\src\app\components

echo Copie des fichiers d'application...
copy /Y angular-services\example-app\app.component.ts frontend_ocr\src\app\
copy /Y angular-services\example-app\app.component.html frontend_ocr\src\app\
copy /Y angular-services\example-app\app.component.css frontend_ocr\src\app\
copy /Y angular-services\example-app\app.config.ts frontend_ocr\src\app\
copy /Y angular-services\example-app\main.ts frontend_ocr\src\
copy /Y angular-services\example-app\index.html frontend_ocr\src\
copy /Y angular-services\example-app\styles.css frontend_ocr\src\

echo Installation des dépendances...
cd frontend_ocr
call npm install

echo Terminé! Lancez 'cd frontend_ocr' puis 'ng serve'
```

Ou pour Linux/Mac (`setup.sh`) :

```bash
#!/bin/bash
echo "Création du projet Angular..."
ng new frontend_ocr --standalone --routing=false --style=css --skip-git

echo "Copie des services..."
cp -r angular-services/services frontend_ocr/src/app/

echo "Copie des composants..."
cp -r angular-services/components frontend_ocr/src/app/

echo "Copie des fichiers d'application..."
cp angular-services/example-app/app.component.* frontend_ocr/src/app/
cp angular-services/example-app/app.config.ts frontend_ocr/src/app/
cp angular-services/example-app/main.ts frontend_ocr/src/
cp angular-services/example-app/index.html frontend_ocr/src/
cp angular-services/example-app/styles.css frontend_ocr/src/

echo "Installation des dépendances..."
cd frontend_ocr
npm install

echo "Terminé! Lancez 'cd frontend_ocr' puis 'ng serve'"
```

## ✅ Vérification

Après installation, vérifiez que :

1. ✅ Le backend Flask tourne sur `http://localhost:8082`
2. ✅ Le frontend Angular tourne sur `http://localhost:4100`
3. ✅ Pas d'erreurs dans la console du navigateur
4. ✅ Les deux onglets sont visibles et fonctionnels

## 🐛 Dépannage

### Erreur "Cannot find module"
→ Vérifiez que les dossiers `services/` et `components/` sont bien dans `src/app/`

### Erreur CORS
→ Vérifiez que Flask-CORS est activé dans le backend

### Page blanche
→ Ouvrez la console du navigateur (F12) pour voir les erreurs

## 📞 Besoin d'aide ?

Consultez le README complet dans `angular-services/components/README.md`
