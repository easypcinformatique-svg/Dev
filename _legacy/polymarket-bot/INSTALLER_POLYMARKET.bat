@echo off
chcp 65001 >nul
title Polymarket Bot - Installation et Mise a jour automatique
color 0A

echo ============================================
echo   POLYMARKET HEDGE FUND BOT
echo   Installation / Mise a jour / Deploiement
echo ============================================
echo.

:: Configuration
set "INSTALL_DIR=%USERPROFILE%\Desktop\PolymarketBot"
set "REPO_URL=https://github.com/easypcinformatique-svg/Dev.git"
set "BRANCH=claude/pokymarket-work-MXwve"

:: ================================================
:: ETAPE 1 : Verification des prerequis
:: ================================================
echo [1/5] Verification des prerequis...
echo.

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

:: Verifier pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ATTENTION] pip non trouve, tentative d'installation...
    python -m ensurepip --upgrade 2>nul
)

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

:: ================================================
:: ETAPE 2 : Telechargement / Mise a jour du code
:: ================================================
echo.
echo [2/5] Telechargement et mise a jour du code...

if exist "%INSTALL_DIR%\.git" (
    echo      Dossier existant detecte, mise a jour...
    cd /d "%INSTALL_DIR%"

    :: Sauvegarder les fichiers de config locaux avant le pull
    if exist "bot_configs.json" (
        copy /y "bot_configs.json" "bot_configs.json.bak" >nul 2>&1
        echo      [OK] Sauvegarde des configs locales
    )
    if exist ".env" (
        copy /y ".env" ".env.bak" >nul 2>&1
        echo      [OK] Sauvegarde du fichier .env
    )

    :: Fetch et pull
    git fetch origin %BRANCH% 2>nul
    git checkout %BRANCH% 2>nul
    git pull origin %BRANCH% 2>nul

    if %errorlevel% neq 0 (
        echo      [ATTENTION] Conflit de merge detecte, tentative de resolution...
        git stash 2>nul
        git pull origin %BRANCH% 2>nul
        git stash pop 2>nul
    )

    :: Restaurer les configs locales si elles ont ete ecrasees
    if exist "bot_configs.json.bak" (
        if not exist "bot_configs.json" (
            copy /y "bot_configs.json.bak" "bot_configs.json" >nul 2>&1
        )
        del "bot_configs.json.bak" >nul 2>&1
    )
    if exist ".env.bak" (
        copy /y ".env.bak" ".env" >nul 2>&1
        del ".env.bak" >nul 2>&1
    )

    echo      [OK] Code mis a jour
) else (
    echo      Premiere installation...
    git clone "%REPO_URL%" "%INSTALL_DIR%" 2>nul
    cd /d "%INSTALL_DIR%"
    git checkout %BRANCH% 2>nul
    echo      [OK] Projet clone
)

if not exist "%INSTALL_DIR%\hedge_fund_bot.py" (
    echo [ERREUR] Le fichier hedge_fund_bot.py n'a pas ete telecharge!
    echo Verifie ta connexion internet et reessaye.
    pause
    exit /b
)
echo [OK] Code pret

:: ================================================
:: ETAPE 3 : Installation des dependances
:: ================================================
echo.
echo [3/5] Installation et mise a jour des dependances Python...

:: Mettre a jour pip d'abord
python -m pip install --upgrade pip >nul 2>&1

:: Installer depuis requirements.txt si disponible
if exist "%INSTALL_DIR%\requirements.txt" (
    pip install -r "%INSTALL_DIR%\requirements.txt" --upgrade 2>nul
    echo      [OK] Dependances requirements.txt installees
) else (
    pip install flask numpy pandas scipy requests nltk beautifulsoup4 --upgrade 2>nul
    echo      [OK] Dependances de base installees
)

echo [OK] Dependances a jour

:: ================================================
:: ETAPE 4 : Verification de l'integrite
:: ================================================
echo.
echo [4/5] Verification de l'integrite...

:: Verifier que les fichiers essentiels existent
set "ALL_OK=1"
if not exist "%INSTALL_DIR%\hedge_fund_bot.py" (
    echo [ERREUR] hedge_fund_bot.py manquant!
    set "ALL_OK=0"
)
if not exist "%INSTALL_DIR%\web_dashboard.py" (
    echo [ERREUR] web_dashboard.py manquant!
    set "ALL_OK=0"
)
if not exist "%INSTALL_DIR%\config_manager.py" (
    echo [ERREUR] config_manager.py manquant!
    set "ALL_OK=0"
)

if "%ALL_OK%"=="0" (
    echo [ERREUR] Fichiers manquants! Reessaye l'installation.
    pause
    exit /b
)

:: Verifier que Python peut importer les modules
python -c "import flask; import numpy; import pandas" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ATTENTION] Certains modules Python manquent, reinstallation...
    pip install flask numpy pandas scipy requests 2>nul
)

echo [OK] Tout est en ordre

:: ================================================
:: ETAPE 5 : Demarrage du bot
:: ================================================
echo.
echo ============================================
echo   Le bot va demarrer en mode SIMULATION
echo   (pas de vrai argent)
echo.
echo   Dashboard  : http://localhost:5050
echo   Parametres : http://localhost:5050/settings
echo.
echo   Ouvre ces adresses dans ton navigateur!
echo ============================================
echo.
echo [5/5] Demarrage du bot avec dashboard...
echo.

start http://localhost:5050
timeout /t 2 >nul
python "%INSTALL_DIR%\hedge_fund_bot.py" --dashboard --port 5050

pause
