@echo off
chcp 65001 >nul 2>&1
title Gestion Factures - Pizzeria
color 0B

echo ============================================================
echo    Gestion Factures - Pizzeria
echo ============================================================
echo.

:: Vérifier que l'installation a été faite
if not exist "venv" (
    echo ERREUR : L'installation n'a pas ete faite.
    echo Lancez d'abord "installer_windows.bat"
    echo.
    pause
    exit /b 1
)

:: Activer l'environnement virtuel
call venv\Scripts\activate.bat

echo    Demarrage du serveur...
echo    L'application va s'ouvrir dans votre navigateur.
echo.
echo    Pour arreter : fermez cette fenetre ou appuyez sur CTRL+C
echo ============================================================
echo.

:: Ouvrir le navigateur après 2 secondes
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Lancer le serveur Flask
python run.py
