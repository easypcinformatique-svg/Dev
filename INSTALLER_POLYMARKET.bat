@echo off
chcp 65001 >nul
title Polymarket Bot - Installation automatique
color 0A

echo ============================================
echo   INSTALLATION POLYMARKET HEDGE FUND BOT
echo ============================================
echo.

:: Trouver le bureau
set "INSTALL_DIR=%USERPROFILE%\Desktop\PolymarketBot"

:: Verifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe!
    echo Telecharge-le ici : https://www.python.org/downloads/
    echo IMPORTANT : Coche "Add Python to PATH" pendant l'installation!
    pause
    start https://www.python.org/downloads/
    exit /b
)
echo [OK] Python trouve
python --version

:: Verifier Git
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Git n'est pas installe!
    echo Telecharge-le ici : https://git-scm.com/download/win
    pause
    start https://git-scm.com/download/win
    exit /b
)
echo [OK] Git trouve

echo.
echo [1/4] Telechargement du projet sur le Bureau...
if exist "%INSTALL_DIR%" (
    echo      Dossier existe deja, mise a jour...
    cd /d "%INSTALL_DIR%"
    git fetch origin
    git checkout claude/pokymarket-work-MXwve
    git pull origin claude/pokymarket-work-MXwve
) else (
    git clone https://github.com/easypcinformatique-svg/Dev.git "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
    git checkout claude/pokymarket-work-MXwve
)

if not exist "%INSTALL_DIR%\hedge_fund_bot.py" (
    echo [ERREUR] Le fichier hedge_fund_bot.py n'a pas ete telecharge!
    echo Verifie ta connexion internet et reessaye.
    pause
    exit /b
)
echo [OK] Projet telecharge

echo.
echo [2/4] Installation des dependances Python...
pip install flask numpy pandas scipy requests nltk beautifulsoup4 2>nul
echo [OK] Dependances installees

echo.
echo [3/4] Tout est pret!
echo.
echo ============================================
echo   Le bot va demarrer en mode SIMULATION
echo   (pas de vrai argent)
echo.
echo   Dashboard : http://localhost:5050
echo   Ouvre cette adresse dans ton navigateur!
echo ============================================
echo.
echo [4/4] Demarrage du bot...
echo.

start http://localhost:5050
timeout /t 2 >nul
python "%INSTALL_DIR%\hedge_fund_bot.py" --dashboard --port 5050

pause
