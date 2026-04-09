"""
Recherche de transactions immobilières DVF > 500 000€
dans un rayon de 5km autour du 15 boulevard Marius Bremond, 13015 Marseille.

Utilise :
- API adresse.data.gouv.fr pour le géocodage
- API DVF du CEREMA (apidf-preprod.cerema.fr) pour les transactions
- API DVF Etalab en fallback
"""
import requests
import json
import math
import time

# === 1. Géocodage de l'adresse ===
ADRESSE = "15 boulevard marius bremond 13015 marseille"
RAYON_KM = 5
SEUIL_EUROS = 500000

print(f"{'=' * 80}")
print(f" RECHERCHE DE TRANSACTIONS IMMOBILIÈRES > {SEUIL_EUROS:,.0f} €".replace(",", " "))
print(f" Autour de : {ADRESSE}")
print(f" Rayon : {RAYON_KM} km")
print(f"{'=' * 80}\n")

print("[1/4] Géocodage de l'adresse...")
geo_resp = requests.get(
    "https://api-adresse.data.gouv.fr/search/",
    params={"q": ADRESSE, "limit": 1},
    timeout=15,
)
geo_resp.raise_for_status()
geo_data = geo_resp.json()

if not geo_data.get("features"):
    print("ERREUR : Impossible de géocoder l'adresse.")
    exit(1)

feature = geo_data["features"][0]
center_lon, center_lat = feature["geometry"]["coordinates"]
label = feature["properties"].get("label", ADRESSE)
print(f"   -> {label}")
print(f"   -> Coordonnées : lat={center_lat}, lon={center_lon}\n")


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance en km entre deux points GPS."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(
        math.radians(lat2)
    ) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# === 2. Calcul des codes communes dans le rayon de 5km ===
print("[2/4] Identification des communes dans le rayon de 5km...")

# Utiliser l'API geo.api.gouv.fr pour trouver les communes proches
geo_communes_resp = requests.get(
    "https://geo.api.gouv.fr/communes",
    params={
        "lat": center_lat,
        "lon": center_lon,
        "fields": "nom,code,codesPostaux,centre",
        "format": "json",
        "geometry": "centre",
    },
    timeout=15,
)

# Aussi rechercher par département pour avoir toutes les communes des BdR
dept_resp = requests.get(
    "https://geo.api.gouv.fr/departements/13/communes",
    params={
        "fields": "nom,code,codesPostaux,centre",
        "format": "json",
        "geometry": "centre",
    },
    timeout=15,
)
dept_resp.raise_for_status()
all_communes_13 = dept_resp.json()

# Pour Marseille, on a besoin des arrondissements
# Les arrondissements de Marseille ont des codes INSEE 13201 à 13216
marseille_arrondissements = []
for i in range(1, 17):
    marseille_arrondissements.append(f"132{i:02d}")

# Filtrer les communes dans le rayon de 5km
communes_in_radius = []
for commune in all_communes_13:
    if "centre" not in commune or not commune["centre"]:
        continue
    c_lon, c_lat = commune["centre"]["coordinates"]
    dist = haversine_km(center_lat, center_lon, c_lat, c_lon)
    if dist <= RAYON_KM:
        communes_in_radius.append({
            "code": commune["code"],
            "nom": commune["nom"],
            "distance_km": round(dist, 2),
        })

# Ajouter les arrondissements de Marseille qui sont dans le rayon
# Le centre du 13015 est très proche, on inclut les arrondissements nord
# On va chercher les coordonnées des arrondissements via l'API
arr_resp = requests.get(
    "https://geo.api.gouv.fr/communes",
    params={
        "codeParent": "13055",
        "type": "arrondissement-municipal",
        "fields": "nom,code,centre",
        "format": "json",
        "geometry": "centre",
    },
    timeout=15,
)
if arr_resp.status_code == 200:
    arrondissements = arr_resp.json()
    for arr in arrondissements:
        if "centre" not in arr or not arr["centre"]:
            continue
        a_lon, a_lat = arr["centre"]["coordinates"]
        dist = haversine_km(center_lat, center_lon, a_lat, a_lon)
        if dist <= RAYON_KM:
            communes_in_radius.append({
                "code": arr["code"],
                "nom": arr["nom"],
                "distance_km": round(dist, 2),
            })

# Dédoublonner
seen_codes = set()
unique_communes = []
for c in communes_in_radius:
    if c["code"] not in seen_codes:
        seen_codes.add(c["code"])
        unique_communes.append(c)

unique_communes.sort(key=lambda x: x["distance_km"])

print(f"   -> {len(unique_communes)} communes/arrondissements trouvés dans le rayon :")
for c in unique_communes:
    print(f"      {c['nom']} ({c['code']}) - {c['distance_km']} km")
print()

# === 3. Requête DVF pour chaque commune ===
print("[3/4] Interrogation de l'API DVF pour chaque commune...")

all_transactions = []

# Utiliser l'API DVF du CEREMA
DVF_BASE_URL = "https://apidf-preprod.cerema.fr/dvf_opendata/mutations"

for commune in unique_communes:
    code = commune["code"]
    nom = commune["nom"]

    # Essayer plusieurs années pour plus de résultats
    for annee_min in ["2019-01-01", "2022-01-01"]:
        try:
            params = {
                "code_commune": code,
                "valeur_fonciere_min": SEUIL_EUROS,
                "nature_mutation": "Vente",
                "date_mutation_min": annee_min,
                "page_size": 100,
                "ordering": "-valeur_fonciere",
            }
            r = requests.get(DVF_BASE_URL, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    print(f"   -> {nom} ({code}): {len(results)} transactions > {SEUIL_EUROS:,.0f}€".replace(",", " "))
                    for tx in results:
                        tx["_commune_nom"] = nom
                        tx["_commune_code"] = code
                        tx["_commune_dist"] = commune["distance_km"]
                    all_transactions.extend(results)
                break  # Si on a des résultats, pas besoin de changer la date
            elif r.status_code == 429:
                time.sleep(1)
        except Exception as e:
            print(f"   -> Erreur pour {nom}: {e}")

    time.sleep(0.3)  # Rate limiting

# Si l'API CEREMA ne marche pas, essayer l'API DVF Etalab
if not all_transactions:
    print("\n   -> API CEREMA sans résultats, essai avec l'API DVF Etalab...")
    ETALAB_URL = "https://app.dvf.etalab.gouv.fr/api/mutations"

    for commune in unique_communes:
        code = commune["code"]
        nom = commune["nom"]
        try:
            params = {
                "code_commune": code,
            }
            r = requests.get(ETALAB_URL, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                # Format peut varier
                results = data if isinstance(data, list) else data.get("results", data.get("mutations", []))
                filtered = [tx for tx in results if tx.get("valeur_fonciere", 0) and tx["valeur_fonciere"] >= SEUIL_EUROS]
                if filtered:
                    print(f"   -> {nom} ({code}): {len(filtered)} transactions > {SEUIL_EUROS:,.0f}€".replace(",", " "))
                    for tx in filtered:
                        tx["_commune_nom"] = nom
                        tx["_commune_code"] = code
                        tx["_commune_dist"] = commune["distance_km"]
                    all_transactions.extend(filtered)
        except Exception as e:
            pass
        time.sleep(0.3)

# Aussi essayer l'API cquest en fallback par commune
if not all_transactions:
    print("\n   -> Essai avec l'API cquest.org par commune...")
    CQUEST_URL = "https://api.cquest.org/dvf"

    for commune in unique_communes:
        code = commune["code"]
        nom = commune["nom"]
        try:
            params = {
                "code_commune": code,
                "nature_mutation": "Vente",
            }
            r = requests.get(CQUEST_URL, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                results = data.get("resultats", [])
                filtered = [tx for tx in results if tx.get("valeur_fonciere", 0) and tx["valeur_fonciere"] >= SEUIL_EUROS]
                if filtered:
                    print(f"   -> {nom} ({code}): {len(filtered)} transactions > {SEUIL_EUROS:,.0f}€".replace(",", " "))
                    for tx in filtered:
                        tx["_commune_nom"] = nom
                        tx["_commune_code"] = code
                        tx["_commune_dist"] = commune["distance_km"]
                    all_transactions.extend(filtered)
        except Exception:
            pass
        time.sleep(0.3)

# Dernière tentative : télécharger directement les données DVF géo
if not all_transactions:
    print("\n   -> Essai avec l'API DVF géolocalisée (data.gouv.fr)...")
    # API geo DVF
    try:
        # Bounding box de ~5km autour du point
        delta_lat = RAYON_KM / 111.0
        delta_lon = RAYON_KM / (111.0 * math.cos(math.radians(center_lat)))
        bbox = f"{center_lon - delta_lon},{center_lat - delta_lat},{center_lon + delta_lon},{center_lat + delta_lat}"

        dvf_geo_url = f"https://files.data.gouv.fr/geo-dvf/latest/csv/2023/departements/13.csv.gz"
        print(f"   -> Téléchargement des données DVF 13 (2023)...")
        r = requests.get(dvf_geo_url, timeout=60, stream=True)
        if r.status_code == 200:
            import gzip
            import csv
            import io

            content = gzip.decompress(r.content)
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            count = 0
            for row in reader:
                try:
                    valeur = float(row.get("valeur_fonciere", "0").replace(",", "."))
                    if valeur < SEUIL_EUROS:
                        continue
                    r_lat = row.get("latitude", "")
                    r_lon = row.get("longitude", "")
                    if r_lat and r_lon:
                        dist = haversine_km(center_lat, center_lon, float(r_lat), float(r_lon))
                        if dist <= RAYON_KM:
                            count += 1
                            all_transactions.append({
                                "date_mutation": row.get("date_mutation", ""),
                                "valeur_fonciere": valeur,
                                "adresse_numero": row.get("adresse_numero", ""),
                                "adresse_nom_voie": row.get("adresse_nom_voie", ""),
                                "code_postal": row.get("code_postal", ""),
                                "nom_commune": row.get("nom_commune", ""),
                                "type_local": row.get("type_local", ""),
                                "surface_reelle_bati": row.get("surface_reelle_bati", ""),
                                "surface_terrain": row.get("surface_terrain", ""),
                                "nombre_pieces_principales": row.get("nombre_pieces_principales", ""),
                                "nature_mutation": row.get("nature_mutation", ""),
                                "id_mutation": row.get("id_mutation", ""),
                                "latitude": r_lat,
                                "longitude": r_lon,
                                "_distance_km": round(dist, 2),
                                "_source": "geo-dvf-2023",
                            })
                except (ValueError, TypeError):
                    continue
            print(f"   -> 2023: {count} transactions > {SEUIL_EUROS:,.0f}€ dans le rayon".replace(",", " "))
    except Exception as e:
        print(f"   -> Erreur: {e}")

    # Aussi essayer 2024
    try:
        dvf_geo_url_2024 = f"https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/13.csv.gz"
        print(f"   -> Téléchargement des données DVF 13 (2024)...")
        r = requests.get(dvf_geo_url_2024, timeout=60, stream=True)
        if r.status_code == 200:
            import gzip
            import csv
            import io

            content = gzip.decompress(r.content)
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            count = 0
            for row in reader:
                try:
                    valeur = float(row.get("valeur_fonciere", "0").replace(",", "."))
                    if valeur < SEUIL_EUROS:
                        continue
                    r_lat = row.get("latitude", "")
                    r_lon = row.get("longitude", "")
                    if r_lat and r_lon:
                        dist = haversine_km(center_lat, center_lon, float(r_lat), float(r_lon))
                        if dist <= RAYON_KM:
                            count += 1
                            all_transactions.append({
                                "date_mutation": row.get("date_mutation", ""),
                                "valeur_fonciere": valeur,
                                "adresse_numero": row.get("adresse_numero", ""),
                                "adresse_nom_voie": row.get("adresse_nom_voie", ""),
                                "code_postal": row.get("code_postal", ""),
                                "nom_commune": row.get("nom_commune", ""),
                                "type_local": row.get("type_local", ""),
                                "surface_reelle_bati": row.get("surface_reelle_bati", ""),
                                "surface_terrain": row.get("surface_terrain", ""),
                                "nombre_pieces_principales": row.get("nombre_pieces_principales", ""),
                                "nature_mutation": row.get("nature_mutation", ""),
                                "id_mutation": row.get("id_mutation", ""),
                                "latitude": r_lat,
                                "longitude": r_lon,
                                "_distance_km": round(dist, 2),
                                "_source": "geo-dvf-2024",
                            })
                except (ValueError, TypeError):
                    continue
            print(f"   -> 2024: {count} transactions > {SEUIL_EUROS:,.0f}€ dans le rayon".replace(",", " "))
    except Exception as e:
        print(f"   -> Erreur 2024: {e}")

print(f"\n   -> Total collecté : {len(all_transactions)} transactions\n")

# === 4. Affichage des résultats ===
print("[4/4] Mise en forme des résultats...\n")

# Dédoublonner
seen = set()
unique_transactions = []
for t in all_transactions:
    id_mut = t.get("id_mutation", "")
    valeur = t.get("valeur_fonciere", 0)
    date = t.get("date_mutation", "")
    adresse = f"{t.get('adresse_numero', '')} {t.get('adresse_nom_voie', '')}".strip()
    key = id_mut or f"{valeur}_{date}_{adresse}"
    if key in seen:
        continue
    seen.add(key)

    # Formater
    surface = t.get("surface_reelle_bati", "")
    terrain = t.get("surface_terrain", "")
    pieces = t.get("nombre_pieces_principales", "")
    distance = t.get("_distance_km", t.get("_commune_dist", "N/A"))

    unique_transactions.append({
        "date": date,
        "valeur": float(valeur) if valeur else 0,
        "adresse": adresse,
        "code_postal": t.get("code_postal", "?"),
        "commune": t.get("nom_commune", t.get("_commune_nom", "?")),
        "type_local": t.get("type_local", "?"),
        "surface_bati": surface,
        "surface_terrain": terrain,
        "pieces": pieces,
        "nature": t.get("nature_mutation", "Vente"),
        "distance_km": distance,
    })

# Trier par valeur décroissante
unique_transactions.sort(key=lambda x: x["valeur"], reverse=True)

print(f"{'=' * 100}")
print(f" RÉSULTATS : {len(unique_transactions)} transactions > {SEUIL_EUROS:,.0f} € dans un rayon de {RAYON_KM} km".replace(",", " "))
print(f" Centre : {label} (lat={center_lat}, lon={center_lon})")
print(f"{'=' * 100}\n")

if not unique_transactions:
    print("Aucune transaction trouvée avec ces critères.")
else:
    for i, t in enumerate(unique_transactions, 1):
        print(f"--- Transaction #{i} ---")
        print(f"  Date         : {t['date']}")
        val_str = f"{t['valeur']:,.0f}".replace(",", " ")
        print(f"  Valeur       : {val_str} €")
        print(f"  Adresse      : {t['adresse']}")
        print(f"  Code postal  : {t['code_postal']}")
        print(f"  Commune      : {t['commune']}")
        print(f"  Type         : {t['type_local']}")
        if t['surface_bati']:
            print(f"  Surface bâti : {t['surface_bati']} m²")
        if t['surface_terrain']:
            print(f"  Terrain      : {t['surface_terrain']} m²")
        if t['pieces']:
            print(f"  Pièces       : {t['pieces']}")
        print(f"  Nature       : {t['nature']}")
        print(f"  Distance     : {t['distance_km']} km")
        print()

    # Sauvegarder en JSON
    output_file = "/home/user/Dev/transactions_500k_marseille_5km.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(unique_transactions, f, ensure_ascii=False, indent=2, default=str)
    print(f"Résultats sauvegardés dans : {output_file}")

    # Résumé statistique
    print(f"\n{'=' * 60}")
    print(" RÉSUMÉ STATISTIQUE")
    print(f"{'=' * 60}")
    valeurs = [t["valeur"] for t in unique_transactions]
    print(f"  Nombre de transactions  : {len(valeurs)}")
    print(f"  Valeur minimale         : {min(valeurs):,.0f} €".replace(",", " "))
    print(f"  Valeur maximale         : {max(valeurs):,.0f} €".replace(",", " "))
    print(f"  Valeur moyenne          : {sum(valeurs)/len(valeurs):,.0f} €".replace(",", " "))
    valeurs_sorted = sorted(valeurs)
    median = valeurs_sorted[len(valeurs_sorted) // 2]
    print(f"  Valeur médiane          : {median:,.0f} €".replace(",", " "))

    # Par type
    types = {}
    for t in unique_transactions:
        tp = t["type_local"] or "Inconnu"
        types[tp] = types.get(tp, 0) + 1
    print(f"\n  Par type de bien :")
    for tp, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"    - {tp}: {count}")

    # Par commune
    communes = {}
    for t in unique_transactions:
        c = t["commune"]
        communes[c] = communes.get(c, 0) + 1
    print(f"\n  Par commune :")
    for c, count in sorted(communes.items(), key=lambda x: -x[1]):
        print(f"    - {c}: {count}")

    # Par année
    annees = {}
    for t in unique_transactions:
        if t["date"]:
            annee = t["date"][:4]
            annees[annee] = annees.get(annee, 0) + 1
    print(f"\n  Par année :")
    for a, count in sorted(annees.items()):
        print(f"    - {a}: {count}")
