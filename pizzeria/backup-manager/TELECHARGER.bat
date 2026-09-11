@echo off
chcp 65001 >nul
title Pizza Napoli - Telechargement Backup Manager
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Pizza Napoli - Backup Manager          ║
echo  ║   Telechargement + Installation           ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Créer le dossier
set INSTALL_DIR=%USERPROFILE%\Desktop\PizzaNapoli-Backup
mkdir "%INSTALL_DIR%" 2>nul

echo  Telechargement en cours...
echo.

:: Télécharger les fichiers depuis GitHub
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/easypcinformatique-svg/Dev/master/pizzeria/backup-manager/backup_pizzeria.pyw' -OutFile '%INSTALL_DIR%\backup_pizzeria.pyw'"
echo  [OK] backup_pizzeria.pyw

powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/easypcinformatique-svg/Dev/master/pizzeria/backup-manager/INSTALLER.bat' -OutFile '%INSTALL_DIR%\INSTALLER.bat'"
echo  [OK] INSTALLER.bat

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   Telechargement termine !                ║
echo  ║   Dossier : Bureau\PizzaNapoli-Backup    ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Lancer l'installateur
echo  Lancement de l'installation...
cd "%INSTALL_DIR%"
call INSTALLER.bat
