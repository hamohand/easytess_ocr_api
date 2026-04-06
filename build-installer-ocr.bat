@echo off
echo ===========================================
echo   Génération de l'installeur EasyTess OCR
echo ===========================================

set DIST_DIR=build-ocr-dist
mkdir %DIST_DIR%

echo [1/3] Copie du Backend OCR...
xcopy /E /I /Y backend\app_ocr %DIST_DIR%\backend
mkdir %DIST_DIR%\backend\core_lib
xcopy /E /I /Y backend\core_lib %DIST_DIR%\backend\core_lib

echo [2/3] Compilation du Frontend Angular...
cd frontend_ocr
call npm install
call npm run build
cd ..
mkdir %DIST_DIR%\frontend
xcopy /E /I /Y frontend_ocr\dist\easytess-frontend\browser\* %DIST_DIR%\frontend\

echo [3/3] Creation des scripts de demarrage...
echo python run.py > %DIST_DIR%\backend\start_backend.bat
echo npx http-server ./frontend -p 80 > %DIST_DIR%\start_frontend.bat

echo ===========================================
echo   Termine ! Vous pouvez livrer le dossier "%DIST_DIR%" au client frida-micros-racine.
echo ===========================================
pause
