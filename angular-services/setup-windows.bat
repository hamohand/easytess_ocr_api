@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Installation EasyTess Frontend
echo ========================================
echo.

REM Vérifier si le projet existe déjà
if exist "..\easytess-frontend" (
    echo Le dossier easytess-frontend existe deja.
    echo Suppression et recreation...
    rmdir /s /q ..\easytess-frontend
)

echo.
echo [1/5] Creation du projet Angular (cela peut prendre 2-3 minutes)...
echo.
cd ..
call ng new easytess-frontend --standalone --routing=false --style=css --skip-git --package-manager=npm --skip-install
if errorlevel 1 (
    echo ERREUR: Impossible de creer le projet Angular
    echo Verifiez que Angular CLI est installe: npm install -g @angular/cli
    pause
    exit /b 1
)
cd angular-services

echo.
echo [2/5] Copie des services...
xcopy /E /I /Y services ..\easytess-frontend\src\app\services
if errorlevel 1 (
    echo ERREUR: Impossible de copier les services
    pause
    exit /b 1
)

echo.
echo [3/5] Copie des composants...
xcopy /E /I /Y components ..\easytess-frontend\src\app\components
if errorlevel 1 (
    echo ERREUR: Impossible de copier les composants
    pause
    exit /b 1
)

echo.
echo [4/5] Copie des fichiers d'application...
copy /Y example-app\app.component.ts ..\easytess-frontend\src\app\app.component.ts
copy /Y example-app\app.component.html ..\easytess-frontend\src\app\app.component.html
copy /Y example-app\app.component.css ..\easytess-frontend\src\app\app.component.css
copy /Y example-app\app.config.ts ..\easytess-frontend\src\app\app.config.ts
copy /Y example-app\main.ts ..\easytess-frontend\src\main.ts
copy /Y example-app\index.html ..\easytess-frontend\src\index.html
copy /Y example-app\styles.css ..\easytess-frontend\src\styles.css

echo.
echo [5/5] Installation des dependances npm...
cd ..\easytess-frontend
call npm install
if errorlevel 1 (
    echo ERREUR: Installation npm echouee
    cd ..
    pause
    exit /b 1
)

cd ..

echo.
echo ========================================
echo Installation terminee avec succes!
echo ========================================
echo.
echo Pour lancer l'application:
echo   1. cd easytess-frontend
echo   2. ng serve --port 4300 --open
echo.
echo L'application sera accessible sur http://localhost:4300
echo.
pause
