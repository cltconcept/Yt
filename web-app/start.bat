@echo off
chcp 65001 > nul
echo ====================================
echo   YouTube Pipeline - Demarrage
echo ====================================
echo.

REM Verifier que Docker est lance
docker info > nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Docker n'est pas lance !
    echo.
    echo Veuillez lancer Docker Desktop et reessayer.
    echo.
    pause
    exit /b 1
)

REM Creer les dossiers data si necessaires
if not exist "data" mkdir data
if not exist "data\output" mkdir data\output
if not exist "data\uploads" mkdir data\uploads

echo [1/3] Construction des images Docker...
docker compose build
if errorlevel 1 (
    echo Essai avec docker-compose...
    docker-compose build
)

echo.
echo [2/3] Demarrage des conteneurs...
docker compose up -d
if errorlevel 1 (
    docker-compose up -d
)

echo.
echo [3/3] Verification...
timeout /t 5 /nobreak > nul

echo.
echo ====================================
echo   Application demarree !
echo ====================================
echo.
echo   Frontend : http://localhost:3000
echo   Backend  : http://localhost:8000
echo   Settings : http://localhost:3000/settings
echo.
echo   Pour voir les logs : docker compose logs -f
echo   Pour arreter       : docker compose down
echo.

REM Ouvrir automatiquement le navigateur
start http://localhost:3000

pause
