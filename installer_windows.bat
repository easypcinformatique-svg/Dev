@echo off
chcp 65001 >nul 2>&1
title Installation - Gestion Factures Pizzeria
color 0A

echo ============================================================
echo    INSTALLATION - Gestion Factures Pizzeria
echo ============================================================
echo.

:: Vérifier Python
echo [1/5] Verification de Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERREUR : Python n'est pas installe ou pas dans le PATH.
    echo.
    echo Telechargez Python 3.10+ depuis : https://www.python.org/downloads/
    echo IMPORTANT : Cochez "Add Python to PATH" lors de l'installation !
    echo.
    pause
    exit /b 1
)
python --version
echo    OK
echo.

:: Créer l'environnement virtuel
echo [2/5] Creation de l'environnement virtuel...
if not exist "venv" (
    python -m venv venv
    echo    Environnement cree.
) else (
    echo    Environnement existant detecte.
)
echo.

:: Activer et installer les dépendances
echo [3/5] Installation des dependances Python...
call venv\Scripts\activate.bat
pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo ERREUR lors de l'installation des dependances.
    pause
    exit /b 1
)
echo    Dependances installees.
echo.

:: Vérifier/Installer Tesseract
echo [4/5] Verification de Tesseract OCR...
where tesseract >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo    Tesseract OCR n'est pas installe.
    echo    L'application fonctionnera mais sans la lecture automatique OCR.
    echo.
    echo    Pour installer Tesseract (optionnel) :
    echo    1. Allez sur : https://github.com/UB-Mannheim/tesseract/wiki
    echo    2. Telechargez l'installeur Windows 64-bit
    echo    3. Lors de l'installation, cochez "French" dans les langues
    echo    4. Ajoutez le dossier d'installation au PATH systeme
    echo       (par defaut : C:\Program Files\Tesseract-OCR)
    echo.
) else (
    echo    Tesseract detecte.
)

:: Créer le fichier .env s'il n'existe pas
echo [5/5] Configuration...
if not exist ".env" (
    copy .env.example .env >nul
    echo    Fichier .env cree depuis .env.example
    echo    Editez .env pour ajouter vos identifiants Google OAuth
) else (
    echo    Fichier .env existant detecte.
)
echo.

:: Créer le dossier uploads
if not exist "uploads" mkdir uploads

echo ============================================================
echo    INSTALLATION TERMINEE !
echo ============================================================
echo.
echo    Pour lancer l'application : double-cliquez sur "lancer.bat"
echo    Ou tapez : venv\Scripts\activate ^&^& python run.py
echo.
echo    L'application sera accessible sur : http://localhost:5000
echo.
pause
