@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   SCRIPT DE RENOMMAGE - PIZZA NAPOLI CARPENTRAS
echo ============================================================
echo.

set "DOSSIER=C:\Users\xxx\Downloads\Photos-3-001 (1)"

:: Verification du dossier
if not exist "%DOSSIER%" (
    echo ERREUR : Le dossier n'existe pas !
    echo Verifiez le chemin : %DOSSIER%
    pause
    exit /b
)

cd /d "%DOSSIER%"

echo --- Renommage des photos deja identifiees ---
echo.

:: Photos deja nommees
if exist "Cochonnaille .jpg" (
    rename "Cochonnaille .jpg" "pizza-cochonaille-tomate-fromage-jambon-bacon-lardons-jambon-cru-moutarde.jpg"
    echo [OK] Cochonnaille renommee
)

if exist "Milano -EDIT(1).jpg" (
    rename "Milano -EDIT(1).jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-2.jpg"
    echo [OK] Milano EDIT(1) renommee
)

if exist "Milano -EDIT.jpg" (
    rename "Milano -EDIT.jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-3.jpg"
    echo [OK] Milano EDIT renommee
)

if exist "Milano .jpg" (
    rename "Milano .jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-4.jpg"
    echo [OK] Milano (avec espace) renommee
)

if exist "Milano.jpg" (
    rename "Milano.jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-1.jpg"
    echo [OK] Milano renommee
)

if exist "Pizza royale.jpg" (
    rename "Pizza royale.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf.jpg"
    echo [OK] Pizza royale renommee
)

if exist "Saint Jacques .jpg" (
    rename "Saint Jacques .jpg" "pizza-saint-jacques-tomate-fromage-saint-jacques.jpg"
    echo [OK] Saint Jacques renommee
)

if exist "Sweety chèvre.jpg" (
    rename "Sweety chèvre.jpg" "pizza-sweety-chevre-fromage-creme-chevre-lardons-oignons-miel.jpg"
    echo [OK] Sweety chevre renommee
)

if exist "Tartuffo.jpg" (
    rename "Tartuffo.jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe.jpg"
    echo [OK] Tartuffo renommee
)

echo.
echo --- Photos identifiees renommees avec succes ! ---
echo.
echo ============================================================
echo   ATTENTION : Il reste environ 72 photos non identifiees
echo   (nommees par date ex: 20230926_192459.jpg)
echo.
echo   Pour les renommer, ouvrez le fichier correspondances.csv
echo   et remplissez la colonne "nouveau_nom" pour chaque photo.
echo   Puis relancez ce script.
echo ============================================================
echo.

:: Lecture du fichier CSV si il existe
if exist "%DOSSIER%\correspondances.csv" (
    echo --- Renommage depuis correspondances.csv ---
    echo.
    for /f "skip=1 tokens=1,2 delims=;" %%a in ('type "%DOSSIER%\correspondances.csv"') do (
        if not "%%b"=="" (
            if exist "%%a" (
                rename "%%a" "%%b"
                echo [OK] %%a  -^>  %%b
            ) else (
                echo [SKIP] %%a non trouve
            )
        )
    )
    echo.
    echo --- Renommage CSV termine ! ---
)

echo.
echo Termine !
pause
