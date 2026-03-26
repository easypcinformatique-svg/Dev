@echo off
echo ========================================
echo   DEPLOIEMENT DES GUIDES BLOG
echo ========================================

set BLOG=C:\Users\xxx\Desktop\Dev\pizzeria\livraison-site\blog
set REPOS=monteux serres pernes-les-fontaines aubignan loriol-du-comtat

echo.
echo [1/2] Mise a jour du repo principal...
cd C:\Users\xxx\Desktop\Dev
git pull origin master

echo.
echo [2/2] Deploiement sur les repos satellites...

for %%r in (%REPOS%) do (
    echo.
    echo --- %%r ---
    cd %TEMP%
    if exist "livraison-pizza-%%r" (
        cd livraison-pizza-%%r
        git pull origin main
    ) else (
        git clone https://github.com/carpentraspizzanapoli-design/livraison-pizza-%%r.git
        cd livraison-pizza-%%r
    )
    if not exist blog mkdir blog
    xcopy "%BLOG%\blog.css" "blog\" /Y >nul
    for %%f in ("%BLOG%\guide-*.html") do (
        xcopy "%%f" "blog\" /Y >nul
    )
    git add -A
    git diff --cached --quiet || (git commit -m "Update guides" && git push origin main)
    cd %TEMP%
)

echo.
echo ========================================
echo   DEPLOIEMENT TERMINE !
echo ========================================
pause
