@echo off
chcp 65001 >nul 2>&1
title Installation - Gestion Factures Pizzeria
color 0A

echo ============================================================
echo    INSTALLATION - Gestion Factures Pizzeria
echo ============================================================
echo.

:: Trouver la bonne version de Python (3.10-3.13)
echo [1/5] Verification de Python...
set PYTHON_CMD=

:: Essayer py -3.12 d'abord (version recommandee)
py -3.12 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.12
    goto python_found
)

:: Essayer py -3.13
py -3.13 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.13
    goto python_found
)

:: Essayer py -3.11
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.11
    goto python_found
)

:: Essayer py -3.10
py -3.10 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py -3.10
    goto python_found
)

:: Essayer python classique en dernier recours
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto python_found
)

echo.
echo ERREUR : Python 3.10 a 3.13 n'est pas installe.
echo.
echo Telechargez Python 3.12 depuis :
echo https://www.python.org/downloads/release/python-3120/
echo Cliquez sur "Windows installer (64-bit)"
echo IMPORTANT : Cochez "Add Python to PATH" lors de l'installation !
echo.
pause
exit /b 1

:python_found
%PYTHON_CMD% --version
echo    OK (utilise: %PYTHON_CMD%)
echo.

:: Créer l'environnement virtuel
echo [2/5] Creation de l'environnement virtuel...
if not exist "venv" (
    %PYTHON_CMD% -m venv venv
    echo    Environnement cree.
) else (
    echo    Environnement existant detecte.
    echo    Pour reinstaller, supprimez le dossier "venv" et relancez.
)
echo.

:: Activer et installer les dépendances
echo [3/5] Installation des dependances Python...
call venv\Scripts\activate.bat
pip install --quiet -r requirements.txt
if %errorlevel% neq 0 (
    echo ERREUR lors de l'installation des dependances.
    echo Essayez de supprimer le dossier "venv" et relancez ce script.
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
