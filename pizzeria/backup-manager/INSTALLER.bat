@echo off
chcp 65001 >nul
title Pizza Napoli - Installation Backup Manager
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Pizza Napoli - Backup Manager          ║
echo  ║   Installation                            ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Vérifier Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python n'est pas installe.
    echo  [!] Telechargement en cours...
    echo.
    start https://www.python.org/downloads/
    echo  Installez Python puis relancez ce script.
    pause
    exit /b
)

echo  [OK] Python detecte
echo.

:: Créer le raccourci sur le Bureau
echo  Creation du raccourci sur le Bureau...

set SCRIPT_PATH=%~dp0backup_pizzeria.pyw
set DESKTOP=%USERPROFILE%\Desktop

:: Créer un fichier VBS pour générer le raccourci
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\create_shortcut.vbs"
echo sLinkFile = "%DESKTOP%\Pizza Napoli Backup.lnk" >> "%TEMP%\create_shortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\create_shortcut.vbs"
echo oLink.TargetPath = "pythonw.exe" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Arguments = """%SCRIPT_PATH%""" >> "%TEMP%\create_shortcut.vbs"
echo oLink.WorkingDirectory = "%~dp0" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Description = "Pizza Napoli - Backup Manager" >> "%TEMP%\create_shortcut.vbs"
echo oLink.Save >> "%TEMP%\create_shortcut.vbs"

cscript //nologo "%TEMP%\create_shortcut.vbs"
del "%TEMP%\create_shortcut.vbs"

echo.
echo  [OK] Raccourci cree sur le Bureau : "Pizza Napoli Backup"
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Installation terminee !                 ║
echo  ║   Double-cliquez sur le raccourci         ║
echo  ║   "Pizza Napoli Backup" sur le Bureau     ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Lancer l'application
echo  Lancement de l'application...
start "" pythonw.exe "%SCRIPT_PATH%"

pause
