@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   SCRIPT DE RENOMMAGE PHOTOS - PIZZA NAPOLI CARPENTRAS
echo   Reconnaissance visuelle par IA - 89 fichiers
echo ============================================================
echo.

set "DOSSIER=C:\Users\xxx\Downloads\Photos-3-001 (1)"

if not exist "%DOSSIER%" (
    echo ERREUR : Le dossier n'existe pas !
    echo Verifiez le chemin : %DOSSIER%
    pause
    exit /b
)

cd /d "%DOSSIER%"
echo Dossier : %DOSSIER%
echo.

set COUNT=0

:: ============================================================
:: --- NOS COMPOSEES ---
:: ============================================================

:: CANADIENNE - Tomate, fromage, bacon, oeuf
if exist "20240109_203840.jpg" (
    rename "20240109_203840.jpg" "pizza-canadienne-tomate-fromage-bacon-oeuf-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-canadienne 1
)

:: EL PASO - Tomate, fromage, chorizo, poivrons
if exist "20240123_201510.jpg" (
    rename "20240123_201510.jpg" "pizza-el-paso-tomate-fromage-chorizo-poivrons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-el-paso 1
)
if exist "20260320_195604.jpg" (
    rename "20260320_195604.jpg" "pizza-el-paso-tomate-fromage-chorizo-poivrons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-el-paso 2
)

:: FORESTIERE - Tomate, fromage, lardons, oignons, champignons
if exist "20240109_205532.jpg" (
    rename "20240109_205532.jpg" "pizza-forestiere-tomate-fromage-lardons-oignons-champignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-forestiere 1
)

:: PAYSANNE - Tomate, fromage, chevre, lardons, jambon cru
if exist "20250318_193845.jpg" (
    rename "20250318_193845.jpg" "pizza-paysanne-tomate-fromage-chevre-lardons-jambon-cru-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-paysanne 1
)

:: MEGAROYALE - Tomate, fromage, pommes de terre, jambon, champignons, oignons, oeuf
if exist "20230926_204725(1).jpg" (
    rename "20230926_204725(1).jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 1
)
if exist "20230926_204725.jpg" (
    rename "20230926_204725.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 2
)
if exist "20250128_184343.jpg" (
    rename "20250128_184343.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 3
)
if exist "20250128_184345.jpg" (
    rename "20250128_184345.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 4
)
if exist "20250128_184349.jpg" (
    rename "20250128_184349.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-5.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 5
)
if exist "Pizza royale.jpg" (
    rename "Pizza royale.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-6.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 6
)
if exist "Pizza royale~2.jpg" (
    rename "Pizza royale~2.jpg" "pizza-megaroyale-tomate-fromage-pommes-de-terre-jambon-champignons-oignons-oeuf-7.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megaroyale 7
)

:: COCHONAILLE - Tomate, fromage, jambon, bacon, lardons, jambon cru, moutarde
if exist "Cochonnaille .jpg" (
    rename "Cochonnaille .jpg" "pizza-cochonaille-tomate-fromage-jambon-bacon-lardons-jambon-cru-moutarde-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-cochonaille 1
)
if exist "Cochonnaille.jpg" (
    rename "Cochonnaille.jpg" "pizza-cochonaille-tomate-fromage-jambon-bacon-lardons-jambon-cru-moutarde-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-cochonaille 2
)
if exist "20240109_205527.jpg" (
    rename "20240109_205527.jpg" "pizza-cochonaille-tomate-fromage-jambon-bacon-lardons-jambon-cru-moutarde-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-cochonaille 3
)

:: SWEET CHORIZO - Tomate, fromage, chorizo, champignons, poivrons, oignons
if exist "20230926_204721.jpg" (
    rename "20230926_204721.jpg" "pizza-sweet-chorizo-tomate-fromage-chorizo-champignons-poivrons-oignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-sweet-chorizo 1
)
if exist "20250822_193559.jpg" (
    rename "20250822_193559.jpg" "pizza-sweet-chorizo-tomate-fromage-chorizo-champignons-poivrons-oignons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-sweet-chorizo 2
)

:: TARTUFO - Tomate, fromage, jambon, mozza di bufala, huile de truffe
if exist "Tartuffo.jpg" (
    rename "Tartuffo.jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-tartufo 1
)
if exist "Tartuffo (1).jpg" (
    rename "Tartuffo (1).jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-tartufo 2
)
if exist "20250121_200746.jpg" (
    rename "20250121_200746.jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-tartufo 3
)
if exist "20250121_200754.jpg" (
    rename "20250121_200754.jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-tartufo 4
)
if exist "20250121_200759.jpg" (
    rename "20250121_200759.jpg" "pizza-tartufo-tomate-fromage-jambon-mozza-di-bufala-huile-de-truffe-5.jpg"
    set /a COUNT+=1
    echo [OK] pizza-tartufo 5
)

:: ============================================================
:: --- NOS FROMAGES ---
:: ============================================================

:: MOZZA - Tomate, fromage, mozzarella
if exist "20230926_192502.jpg" (
    rename "20230926_192502.jpg" "pizza-mozza-tomate-fromage-mozzarella-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-mozza 1
)
if exist "20250318_193849.jpg" (
    rename "20250318_193849.jpg" "pizza-mozza-tomate-fromage-mozzarella-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-mozza 2
)
if exist "20260320_195835.jpg" (
    rename "20260320_195835.jpg" "pizza-mozza-tomate-fromage-mozzarella-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-mozza 3
)

:: CHEVRE - Tomate, fromage, chevre
if exist "20230926_203906(1).jpg" (
    rename "20230926_203906(1).jpg" "pizza-chevre-tomate-fromage-chevre-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chevre 1
)
if exist "20230926_203906.jpg" (
    rename "20230926_203906.jpg" "pizza-chevre-tomate-fromage-chevre-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chevre 2
)

:: 3 FRO - Tomate, fromage, mozzarella, chevre
if exist "20250704_194150.jpg" (
    rename "20250704_194150.jpg" "pizza-3-fro-tomate-fromage-mozzarella-chevre-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-3-fro 1
)
if exist "20250704_194155.jpg" (
    rename "20250704_194155.jpg" "pizza-3-fro-tomate-fromage-mozzarella-chevre-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-3-fro 2
)

:: 4 FRO - Tomate, fromage, mozzarella, roquefort, chevre
if exist "20230926_202535(1).jpg" (
    rename "20230926_202535(1).jpg" "pizza-4-fro-tomate-fromage-mozzarella-roquefort-chevre-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-4-fro 1
)
if exist "20230926_202535.jpg" (
    rename "20230926_202535.jpg" "pizza-4-fro-tomate-fromage-mozzarella-roquefort-chevre-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-4-fro 2
)
if exist "4Fro.jpg" (
    rename "4Fro.jpg" "pizza-4-fro-tomate-fromage-mozzarella-roquefort-chevre-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-4-fro 3
)
if exist "20260320_195554.jpg" (
    rename "20260320_195554.jpg" "pizza-4-fro-tomate-fromage-mozzarella-roquefort-chevre-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-4-fro 4
)

:: MEGAFRO - Tomate, fromage, mozzarella, roquefort, chevre, raclette
if exist "20250318_195854.jpg" (
    rename "20250318_195854.jpg" "pizza-megafro-tomate-fromage-mozzarella-roquefort-chevre-raclette-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megafro 1
)
if exist "20250425_192825.jpg" (
    rename "20250425_192825.jpg" "pizza-megafro-tomate-fromage-mozzarella-roquefort-chevre-raclette-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megafro 2
)
if exist "20250425_192932.jpg" (
    rename "20250425_192932.jpg" "pizza-megafro-tomate-fromage-mozzarella-roquefort-chevre-raclette-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-megafro 3
)

:: ============================================================
:: --- NOS ALPINES ---
:: ============================================================

:: PYRENEENNE - Tomate, fromage, jambon, jambon cru, raclette
if exist "20230926_202527.jpg" (
    rename "20230926_202527.jpg" "pizza-pyreneenne-tomate-fromage-jambon-jambon-cru-raclette-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-pyreneenne 1
)
if exist "20230926_202531.jpg" (
    rename "20230926_202531.jpg" "pizza-pyreneenne-tomate-fromage-jambon-jambon-cru-raclette-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-pyreneenne 2
)

:: ============================================================
:: --- NOS LEGUMES ---
:: ============================================================

:: MILANO - Tomate, aubergines, fromage, chevre, persillade
if exist "Milano .jpg" (
    rename "Milano .jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-milano 1
)
if exist "Milano.jpg" (
    rename "Milano.jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-milano 2
)
if exist "Milano -EDIT.jpg" (
    rename "Milano -EDIT.jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-milano 3
)
if exist "Milano -EDIT(1).jpg" (
    rename "Milano -EDIT(1).jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-milano 4
)
if exist "20250128_193033.jpg" (
    rename "20250128_193033.jpg" "pizza-milano-tomate-aubergines-fromage-chevre-persillade-5.jpg"
    set /a COUNT+=1
    echo [OK] pizza-milano 5
)

:: VEGETARIENNE - Tomate, aubergines, fromage, champignons, poivrons, artichaut, basilic
if exist "20230926_203901.jpg" (
    rename "20230926_203901.jpg" "pizza-vegetarienne-tomate-aubergines-fromage-champignons-poivrons-artichaut-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-vegetarienne 1
)
if exist "20260320_195830.jpg" (
    rename "20260320_195830.jpg" "pizza-vegetarienne-tomate-aubergines-fromage-champignons-poivrons-artichaut-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-vegetarienne 2
)

:: ============================================================
:: --- NOS CARNIVORES ---
:: ============================================================

:: BUFFALO - Tomate, fromage, viande hachee, oignons
if exist "20240123_202554.jpg" (
    rename "20240123_202554.jpg" "pizza-manhattan-tomate-fromage-viande-hachee-oignons-chevre-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-manhattan 1
)

:: ARMENIENNE - Tomate, fromage, viande hachee, oignons, poivrons
if exist "20230926_192459.jpg" (
    rename "20230926_192459.jpg" "pizza-armenienne-tomate-fromage-viande-hachee-oignons-poivrons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-armenienne 1
)
if exist "20240109_203836.jpg" (
    rename "20240109_203836.jpg" "pizza-armenienne-tomate-fromage-viande-hachee-oignons-poivrons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-armenienne 2
)
if exist "20250822_193542.jpg" (
    rename "20250822_193542.jpg" "pizza-armenienne-tomate-fromage-viande-hachee-oignons-poivrons-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-armenienne 3
)
if exist "20250822_193543.jpg" (
    rename "20250822_193543.jpg" "pizza-armenienne-tomate-fromage-viande-hachee-oignons-poivrons-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-armenienne 4
)

:: BOLOGNAISE - Tomate, fromage, viande hachee, oignons, champignons
if exist "20250919_204637.jpg" (
    rename "20250919_204637.jpg" "pizza-bolognaise-tomate-fromage-viande-hachee-oignons-champignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-bolognaise 1
)

:: BARAKO - Tomate, fromage, viande hachee, bacon, oignons
if exist "20250128_185611.jpg" (
    rename "20250128_185611.jpg" "pizza-barako-tomate-fromage-viande-hachee-bacon-oignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-barako 1
)
if exist "20250128_185616.jpg" (
    rename "20250128_185616.jpg" "pizza-barako-tomate-fromage-viande-hachee-bacon-oignons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-barako 2
)
if exist "20250128_185620.jpg" (
    rename "20250128_185620.jpg" "pizza-barako-tomate-fromage-viande-hachee-bacon-oignons-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-barako 3
)

:: CIRCUS - Tomate, fromage, viande hachee, chorizo, merguez, oignons
if exist "20250919_204640.jpg" (
    rename "20250919_204640.jpg" "pizza-circus-tomate-fromage-viande-hachee-chorizo-merguez-oignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-circus 1
)

:: KEBAB - Tomate, fromage, kebab, oignons, sauce blanche
if exist "20250709_202005.jpg" (
    rename "20250709_202005.jpg" "pizza-kebab-tomate-fromage-kebab-oignons-sauce-blanche-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kebab 1
)
if exist "20250709_202015.jpg" (
    rename "20250709_202015.jpg" "pizza-kebab-tomate-fromage-kebab-oignons-sauce-blanche-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kebab 2
)
if exist "20250709_202019.jpg" (
    rename "20250709_202019.jpg" "pizza-kebab-tomate-fromage-kebab-oignons-sauce-blanche-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kebab 3
)
if exist "20250709_202024.jpg" (
    rename "20250709_202024.jpg" "pizza-kebab-tomate-fromage-kebab-oignons-sauce-blanche-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kebab 4
)

:: CHILIENNE - Tomate, fromage, poulet, poivrons, sauce Curry
if exist "20240123_204034-EDIT.jpg" (
    rename "20240123_204034-EDIT.jpg" "pizza-chilienne-tomate-fromage-poulet-poivrons-sauce-curry-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chilienne 1
)
if exist "20240123_204034.jpg" (
    rename "20240123_204034.jpg" "pizza-chilienne-tomate-fromage-poulet-poivrons-sauce-curry-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chilienne 2
)
if exist "20250425_192833.jpg" (
    rename "20250425_192833.jpg" "pizza-chilienne-tomate-fromage-poulet-poivrons-sauce-curry-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chilienne 3
)
if exist "20250425_192941.jpg" (
    rename "20250425_192941.jpg" "pizza-chilienne-tomate-fromage-poulet-poivrons-sauce-curry-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chilienne 4
)
if exist "20260320_195559.jpg" (
    rename "20260320_195559.jpg" "pizza-chilienne-tomate-fromage-poulet-poivrons-sauce-curry-5.jpg"
    set /a COUNT+=1
    echo [OK] pizza-chilienne 5
)

:: ORIENTALE - Tomate, fromage, merguez, oignons, poivrons
if exist "20240109_203230.jpg" (
    rename "20240109_203230.jpg" "pizza-orientale-tomate-fromage-merguez-oignons-poivrons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-orientale 1
)
if exist "20250919_204633.jpg" (
    rename "20250919_204633.jpg" "pizza-orientale-tomate-fromage-merguez-oignons-poivrons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-orientale 2
)

:: KIDECHIRE - Tomate, fromage, chorizo, merguez, Tabasco
if exist "20250704_194130.jpg" (
    rename "20250704_194130.jpg" "pizza-kidechire-tomate-fromage-chorizo-merguez-tabasco-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kidechire 1
)
if exist "20250704_194145.jpg" (
    rename "20250704_194145.jpg" "pizza-kidechire-tomate-fromage-chorizo-merguez-tabasco-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kidechire 2
)
if exist "20250822_193552.jpg" (
    rename "20250822_193552.jpg" "pizza-kidechire-tomate-fromage-chorizo-merguez-tabasco-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-kidechire 3
)

:: BURGER - Tomate, fromage, viande hachee, oignons, cheddar, cornichons, sauce Burger
if exist "20250425_192814.jpg" (
    rename "20250425_192814.jpg" "pizza-burger-tomate-fromage-viande-hachee-oignons-cheddar-cornichons-sauce-burger-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-burger 1
)
if exist "20250425_192821.jpg" (
    rename "20250425_192821.jpg" "pizza-burger-tomate-fromage-viande-hachee-oignons-cheddar-cornichons-sauce-burger-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-burger 2
)
if exist "20250425_192921.jpg" (
    rename "20250425_192921.jpg" "pizza-burger-tomate-fromage-viande-hachee-oignons-cheddar-cornichons-sauce-burger-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-burger 3
)
if exist "20250425_192925.jpg" (
    rename "20250425_192925.jpg" "pizza-burger-tomate-fromage-viande-hachee-oignons-cheddar-cornichons-sauce-burger-4.jpg"
    set /a COUNT+=1
    echo [OK] pizza-burger 4
)

:: APHRODITE - Tomate, fromage, viande hachee, bacon, poulet, merguez, poivrons, sauce BBQ
if exist "20250919_204629.jpg" (
    rename "20250919_204629.jpg" "pizza-aphrodite-tomate-fromage-viande-hachee-bacon-poulet-merguez-poivrons-sauce-bbq-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-aphrodite 1
)

:: ============================================================
:: --- NOS PIZZAS BLANCHES ---
:: ============================================================

:: FLAMKEUCH - Fromage, creme, lardons, oignons
if exist "20250128_185607.jpg" (
    rename "20250128_185607.jpg" "pizza-flamkeuch-fromage-creme-lardons-oignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-flamkeuch 1
)

:: NAPOLI blanche - Fromage, creme, chevre, mozzarella, roquefort
if exist "20240123_201513.jpg" (
    rename "20240123_201513.jpg" "pizza-napoli-fromage-creme-chevre-mozzarella-roquefort-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-napoli 1
)

:: SWEETY CHEVRE - Fromage, creme, chevre, lardons, oignons, miel
if exist "Sweety chèvre.jpg" (
    rename "Sweety chèvre.jpg" "pizza-sweety-chevre-fromage-creme-chevre-lardons-oignons-miel-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-sweety-chevre 1
)

:: SAUMON - Fromage, creme, saumon
if exist "20260320_195613.jpg" (
    rename "20260320_195613.jpg" "pizza-saumon-fromage-creme-saumon-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-saumon 1
)

:: CAMEMBERT - Fromage, creme, jambon, pomme de terre, oignons, camembert, persillade
if exist "20240109_201216.jpg" (
    rename "20240109_201216.jpg" "pizza-camembert-fromage-creme-jambon-pomme-de-terre-oignons-camembert-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-camembert 1
)
if exist "20250128_185438.jpg" (
    rename "20250128_185438.jpg" "pizza-camembert-fromage-creme-jambon-pomme-de-terre-oignons-camembert-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-camembert 2
)
if exist "20250128_185449.jpg" (
    rename "20250128_185449.jpg" "pizza-camembert-fromage-creme-jambon-pomme-de-terre-oignons-camembert-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-camembert 3
)

:: DAUPHINOISE - Fromage, creme, viande hachee, pomme de terre, lardons, oignons, persillade
if exist "20250128_185526.jpg" (
    rename "20250128_185526.jpg" "pizza-dauphinoise-fromage-creme-viande-hachee-pomme-de-terre-lardons-oignons-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-dauphinoise 1
)
if exist "20250128_185551.jpg" (
    rename "20250128_185551.jpg" "pizza-dauphinoise-fromage-creme-viande-hachee-pomme-de-terre-lardons-oignons-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-dauphinoise 2
)
if exist "20250128_185559.jpg" (
    rename "20250128_185559.jpg" "pizza-dauphinoise-fromage-creme-viande-hachee-pomme-de-terre-lardons-oignons-3.jpg"
    set /a COUNT+=1
    echo [OK] pizza-dauphinoise 3
)

:: ============================================================
:: --- HORS FLYER (speciales) ---
:: ============================================================

:: NAPOLITAINE (anchois) - du menu site web
if exist "20260320_191600.jpg" (
    rename "20260320_191600.jpg" "pizza-napolitaine-sauce-tomate-anchois-olives-noires-capres-origan-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-napolitaine 1
)
if exist "20260320_191604.jpg" (
    rename "20260320_191604.jpg" "pizza-napolitaine-sauce-tomate-anchois-olives-noires-capres-origan-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-napolitaine 2
)

:: SAINT JACQUES - pizza fruits de mer (speciale)
if exist "Saint Jacques .jpg" (
    rename "Saint Jacques .jpg" "pizza-saint-jacques-fromage-fruits-de-mer-1.jpg"
    set /a COUNT+=1
    echo [OK] pizza-saint-jacques 1
)

:: PAYSANNE variante (jambon + chevre)
if exist "20240123_201507.jpg" (
    rename "20240123_201507.jpg" "pizza-paysanne-tomate-fromage-chevre-lardons-jambon-cru-2.jpg"
    set /a COUNT+=1
    echo [OK] pizza-paysanne 2
)

:: ============================================================
:: --- VIDEOS (renommage simple) ---
:: ============================================================

if exist "20250128_185539.mp4" (
    rename "20250128_185539.mp4" "video-pizza-napoli-preparation-1.mp4"
    set /a COUNT+=1
    echo [OK] video 1
)
if exist "20250321_183704-CINEMATIC.mp4" (
    rename "20250321_183704-CINEMATIC.mp4" "video-pizza-napoli-cinematic-1.mp4"
    set /a COUNT+=1
    echo [OK] video cinematic 1
)
if exist "20250328_185040-CINEMATIC.mp4" (
    rename "20250328_185040-CINEMATIC.mp4" "video-pizza-napoli-cinematic-2.mp4"
    set /a COUNT+=1
    echo [OK] video cinematic 2
)
if exist "20250330_185441-CINEMATIC.mp4" (
    rename "20250330_185441-CINEMATIC.mp4" "video-pizza-napoli-cinematic-3.mp4"
    set /a COUNT+=1
    echo [OK] video cinematic 3
)
if exist "20250411_170910-CINEMATIC.mp4" (
    rename "20250411_170910-CINEMATIC.mp4" "video-pizza-napoli-cinematic-4.mp4"
    set /a COUNT+=1
    echo [OK] video cinematic 4
)
if exist "20250704_194133.mp4" (
    rename "20250704_194133.mp4" "video-pizza-napoli-preparation-2.mp4"
    set /a COUNT+=1
    echo [OK] video 2
)
if exist "20250822_193510.mp4" (
    rename "20250822_193510.mp4" "video-pizza-napoli-preparation-3.mp4"
    set /a COUNT+=1
    echo [OK] video 3
)
if exist "20250822_193510_1.mp4" (
    rename "20250822_193510_1.mp4" "video-pizza-napoli-preparation-4.mp4"
    set /a COUNT+=1
    echo [OK] video 4
)
if exist "20250822_193510_1_1.mp4" (
    rename "20250822_193510_1_1.mp4" "video-pizza-napoli-preparation-5.mp4"
    set /a COUNT+=1
    echo [OK] video 5
)
if exist "20250919_204602.mp4" (
    rename "20250919_204602.mp4" "video-pizza-napoli-preparation-6.mp4"
    set /a COUNT+=1
    echo [OK] video 6
)

echo.
echo ============================================================
echo   TERMINE ! %COUNT% fichiers renommes avec succes.
echo ============================================================
echo.
pause
