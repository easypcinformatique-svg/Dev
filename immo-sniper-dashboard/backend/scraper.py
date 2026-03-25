"""
Scraper multi-sources pour annonces immobilières réelles.
Source principale : BienIci (API JSON) — annonces actives avec liens directs.
Comparaison prix : DVF (data.gouv.fr) — transactions notariales pour calculer les décotes.
"""
import requests
import gzip
import csv
import io
import time
import re
import hashlib
import json
from datetime import datetime
from collections import defaultdict

try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False
    print("[WARN] curl_cffi non installé, fallback sur requests")

# ── Configuration zone de recherche ──
VILLES_RECHERCHE = [
    "vitrolles", "marignane", "les pennes mirabeau", "gignac la nerthe",
    "rognac", "marseille", "aix en provence", "carry le rouet",
    "chateauneuf les martigues", "martigues", "berre l etang",
    "gardanne", "bouc bel air", "cabries", "septemes les vallons",
    "velaux", "ensuès la redonne", "sausset les pins", "istres",
    "la ciotat",
]

CODES_POSTAUX_SURVEILLES = [
    "13170", "13127", "13700", "13180", "13340", "13130",
    "13220", "13620", "13500", "13100", "13120", "13880",
    "13240", "13320", "13480", "13960", "13820",
    "13001", "13002", "13003", "13004", "13005", "13006",
    "13007", "13008", "13009", "13010", "13011", "13012",
    "13013", "13014", "13015", "13016", "13600", "13800",
]


def _gen_id(source, key):
    return hashlib.md5(f"{source}:{key}".encode()).hexdigest()[:12]


def _detect_mots_cles(text):
    """Détecte les mots-clés d'urgence dans le texte."""
    if not text:
        return []
    text_lower = text.lower()
    keywords = {
        "succession": "succession", "divorce": "divorce", "urgent": "urgent",
        "liquidation": "liquidation", "mutation": "mutation", "vente rapide": "vente rapide",
        "travaux": "travaux", "à rénover": "à rénover", "baisse de prix": "baisse de prix",
        "négociable": "négociable", "viager": "viager", "départ": "départ",
        "cause déménagement": "déménagement", "idéal investisseur": "investisseur",
        "première offre": "première offre", "exclusivité": "exclusivité",
        "occupé": "occupé", "libre": "libre de suite",
    }
    return [label for k, label in keywords.items() if k in text_lower]


def _parse_age(date_str):
    """Convertit une date ISO en ancienneté lisible."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        diff = datetime.now().timestamp() - dt.timestamp()
        if diff < 3600:
            return f"{max(1,int(diff/60))}min"
        elif diff < 86400:
            h = int(diff / 3600)
            m = int((diff % 3600) / 60)
            return f"{h}h{m:02d}"
        elif diff < 86400 * 30:
            return f"{int(diff/86400)}j"
        else:
            return f"{int(diff/86400/30)}mois"
    except:
        return "?"


# ──────────────────────────────────────────────
# SOURCE : BienIci (API JSON — annonces actives)
# ──────────────────────────────────────────────

def _get_bienici_session():
    """Crée une session BienIci avec cookies."""
    if HAS_CFFI:
        session = cffi_requests.Session(impersonate="chrome")
    else:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        })
    # Charger la page d'accueil pour les cookies
    try:
        session.get("https://www.bienici.com/", timeout=10)
    except:
        pass
    return session


def _get_zone_ids(session, villes):
    """Récupère les zoneIds BienIci pour les villes données."""
    zone_ids = []
    for ville in villes:
        try:
            r = session.get(f"https://res.bienici.com/suggest.json?q={ville}", timeout=8)
            if r.status_code == 200:
                results = r.json()
                if results:
                    zones = results[0].get("zoneIds", [])
                    zone_ids.extend(zones)
                    print(f"[BienIci] {results[0].get('name')}: zones={zones}")
            time.sleep(0.2)
        except Exception as e:
            print(f"[BienIci] Erreur suggest {ville}: {e}")
    return list(set(zone_ids))


def scrape_bienici():
    """Scrape les annonces actives depuis l'API BienIci."""
    annonces = []
    try:
        session = _get_bienici_session()
        zone_ids = _get_zone_ids(session, VILLES_RECHERCHE)

        if not zone_ids:
            print("[BienIci] Aucun zoneId trouvé")
            return annonces

        print(f"[BienIci] Recherche dans {len(zone_ids)} zones...")

        # Récupérer les annonces par batch (max 100 par requête)
        property_types = ["house", "flat", "land", "parking", "office", "building"]
        type_map = {
            "house": "Maison", "flat": "Appartement", "land": "Terrain",
            "parking": "Parking", "office": "Local commercial", "building": "Immeuble",
        }

        for page_from in range(0, 500, 100):
            filters = {
                "size": 100,
                "from": page_from,
                "filterType": "buy",
                "propertyType": property_types,
                "zoneIdsByTypes": {"zoneIds": zone_ids},
                "sortBy": "publicationDate",
                "sortOrder": "desc",
            }

            try:
                params = json.dumps(filters)
                r = session.get(
                    f"https://www.bienici.com/realEstateAds.json?filters={params}",
                    timeout=20,
                )

                if r.status_code != 200:
                    print(f"[BienIci] Code {r.status_code} page {page_from}")
                    break

                data = r.json()
                ads = data.get("realEstateAds", [])
                total = data.get("total", 0)

                if not ads:
                    break

                for ad in ads:
                    try:
                        ad_id = ad.get("id", "")
                        prix = ad.get("price")
                        if not prix or prix <= 0:
                            continue

                        surface = ad.get("surfaceArea", 0) or 0
                        prop_type = ad.get("propertyType", "")
                        type_bien = type_map.get(prop_type, "Autre")
                        ville = ad.get("city", "")
                        cp = ad.get("postalCode", "")
                        pieces = ad.get("roomsQuantity") or None
                        dpe = ad.get("energyClassification") or None
                        terrain = ad.get("landSurfaceArea") or None

                        pub_date = ad.get("publicationDate", "")
                        modif_date = ad.get("modificationDate", "")
                        age = _parse_age(pub_date) if pub_date else "?"
                        try:
                            age_ts = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).timestamp()
                        except:
                            age_ts = time.time()

                        surface_val = round(surface) if surface else 0
                        prix_m2 = round(prix / surface_val) if surface_val > 0 else 0

                        description = ad.get("description", "")
                        title = ad.get("title", "") or f"{type_bien} {surface_val}m² {ville}"

                        # Lien DIRECT vers l'annonce
                        annonce_url = f"https://www.bienici.com/annonce/{ad_id}"

                        # Déterminer vendeur
                        account_type = ad.get("accountType", "")
                        vendeur = "agence" if account_type in ("agency", "network") else "particulier"

                        # Photos
                        photos = ad.get("photos", [])
                        photo = photos[0].get("url", "") if photos else ""

                        annonces.append({
                            "id": _gen_id("BienIci", ad_id),
                            "ad_id": ad_id,
                            "type": type_bien,
                            "ville": ville,
                            "cp": cp,
                            "prix": int(prix),
                            "surface": surface_val,
                            "terrain": round(terrain) if terrain else None,
                            "pieces": pieces,
                            "prix_m2": prix_m2,
                            "dpe": dpe if dpe and dpe in "ABCDEFG" else None,
                            "source": "BienIci",
                            "vendeur": vendeur,
                            "age": age,
                            "age_ts": age_ts,
                            "mots": _detect_mots_cles(f"{title} {description}"),
                            "url": annonce_url,
                            "titre": title,
                            "photo": photo,
                            "statut": "nouveau",
                            "est_enchere": False,
                        })

                    except Exception as e:
                        continue

                print(f"[BienIci] Page {page_from}: {len(ads)} annonces (total: {total})")
                time.sleep(0.3)

                if page_from + 100 >= total:
                    break

            except Exception as e:
                print(f"[BienIci] Erreur page {page_from}: {e}")
                break

        print(f"[BienIci] Total: {len(annonces)} annonces récupérées")

    except Exception as e:
        print(f"[BienIci] Erreur globale: {e}")

    return annonces


# ──────────────────────────────────────────────
# DVF : Prix médians pour le scoring
# ──────────────────────────────────────────────

_dvf_medians = {}
_dvf_loaded = False


def _load_dvf_medians():
    """Charge les médianes DVF depuis data.gouv.fr."""
    global _dvf_medians, _dvf_loaded

    if _dvf_loaded:
        return _dvf_medians

    try:
        print("[DVF] Téléchargement données 2024 dept 13...")
        url = "https://files.data.gouv.fr/geo-dvf/latest/csv/2024/departements/13.csv.gz"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            print(f"[DVF] Erreur {resp.status_code}")
            _dvf_loaded = True
            return _dvf_medians

        data = gzip.decompress(resp.content).decode("utf-8")
        reader = csv.DictReader(io.StringIO(data))

        by_key = defaultdict(list)
        for row in reader:
            if row.get("nature_mutation") != "Vente":
                continue
            cp = row.get("code_postal", "")
            type_local = row.get("type_local", "").strip()
            valeur = row.get("valeur_fonciere", "0").replace(",", ".")
            surface = float(row.get("surface_reelle_bati", 0) or 0)

            if not type_local or not surface or surface < 10:
                continue

            try:
                prix = float(valeur)
                if prix < 10000:
                    continue
                prix_m2 = prix / surface
                if prix_m2 < 100 or prix_m2 > 20000:
                    continue

                # Normaliser le type
                if "Maison" in type_local:
                    t = "Maison"
                elif "Appartement" in type_local:
                    t = "Appartement"
                else:
                    t = "Local commercial"

                by_key[(cp, t)].append(prix_m2)
                by_key[(cp, "all")].append(prix_m2)
            except:
                continue

        for key, values in by_key.items():
            values.sort()
            _dvf_medians[key] = round(values[len(values) // 2])

        print(f"[DVF] {len(_dvf_medians)} médianes calculées")
        _dvf_loaded = True

    except Exception as e:
        print(f"[DVF] Erreur: {e}")
        _dvf_loaded = True

    return _dvf_medians


# Fallback médians si DVF pas dispo
FALLBACK_MEDIANS = {
    "13127": 2450, "13700": 2800, "13170": 3100, "13180": 2680,
    "13340": 2750, "13130": 2100, "13220": 2600, "13620": 3200,
    "13500": 2050, "13100": 3450, "13001": 3000, "13002": 2800,
    "13003": 2400, "13004": 2600, "13005": 3100, "13006": 3500,
    "13007": 3800, "13008": 3500, "13009": 3300, "13010": 2700,
    "13011": 2500, "13012": 2800, "13013": 2600, "13014": 2200,
    "13015": 2000, "13016": 2500, "13120": 2800, "13320": 3200,
    "13480": 3000, "13240": 2500, "13600": 3400, "13800": 2300,
}


# ──────────────────────────────────────────────
# SCORING
# ──────────────────────────────────────────────

MOTS_BONUS = {
    "succession": 15, "divorce": 12, "urgent": 10, "liquidation": 15,
    "mutation": 8, "vente rapide": 10, "à saisir": 6, "départ": 5,
    "négociable": 4, "déménagement": 5, "travaux": 3, "à rénover": 3,
    "baisse de prix": 8, "viager": 2, "investisseur": 3,
    "première offre": 5, "libre de suite": 3,
}


def score_annonce(a, medians):
    """Calcule le score d'opportunité (0-100)."""
    score = 25  # Base

    # 1. Décote par rapport à la médiane DVF locale (max 40 pts)
    cp = a.get("cp", "")
    type_bien = a.get("type", "Maison")
    median = medians.get((cp, type_bien)) or medians.get((cp, "all")) or FALLBACK_MEDIANS.get(cp)

    if median:
        a["median_m2"] = median
        if a["prix_m2"] and a["prix_m2"] > 0:
            decote = round((1 - a["prix_m2"] / median) * 100, 1)
            a["decote"] = max(0, decote)
            if decote >= 40:
                score += 40
            elif decote >= 30:
                score += 32
            elif decote >= 20:
                score += 22
            elif decote >= 15:
                score += 15
            elif decote >= 10:
                score += 8
            elif decote >= 5:
                score += 3
            else:
                score -= 10
        else:
            a["decote"] = 0
    else:
        a["median_m2"] = 0
        a["decote"] = 0

    # 2. Mots-clés d'urgence (max 25 pts cumulés)
    mot_bonus = sum(MOTS_BONUS.get(m, 2) for m in a.get("mots", []))
    score += min(25, mot_bonus)

    # 3. Vendeur particulier (+5 pts)
    if a.get("vendeur") == "particulier":
        score += 5

    # 4. Fraîcheur de l'annonce (max 10 pts)
    age = a.get("age", "")
    if "min" in age:
        score += 10
    elif "h" in age:
        h = int(re.search(r"(\d+)h", age).group(1)) if re.search(r"(\d+)h", age) else 24
        if h <= 1:
            score += 8
        elif h <= 3:
            score += 5
        elif h <= 6:
            score += 3

    # 5. DPE malus
    if a.get("dpe") in ("F", "G"):
        score -= 5

    # 6. Petits prix attractifs
    if a["prix"] < 100000 and type_bien in ("Maison", "Appartement"):
        score += 5
    elif a["prix"] < 150000 and type_bien in ("Maison", "Appartement"):
        score += 2

    # Clamp
    score = max(0, min(100, score))
    a["score"] = score

    if score >= 80:
        a["niveau"] = "OPPORTUNITE EXCEPTIONNELLE"
    elif score >= 65:
        a["niveau"] = "FORTE OPPORTUNITE"
    elif score >= 50:
        a["niveau"] = "OPPORTUNITE"
    else:
        a["niveau"] = "A SURVEILLER"

    return a


# ──────────────────────────────────────────────
# ORCHESTRATEUR
# ──────────────────────────────────────────────

def scan_all_sources():
    """Lance le scan complet et retourne les annonces scorées."""
    print("[SCAN] Démarrage du scan multi-sources...")
    start = time.time()

    # 1. Charger les médianes DVF pour le scoring
    medians = _load_dvf_medians()

    # 2. Scraper les annonces actives
    all_annonces = scrape_bienici()

    # 3. Scorer chaque annonce
    scored = [score_annonce(a, medians) for a in all_annonces]

    # 4. Trier par score décroissant
    scored.sort(key=lambda x: x["score"], reverse=True)

    # 5. Garder les meilleures
    scored = scored[:500]

    elapsed = round(time.time() - start, 1)
    print(f"[SCAN] Terminé en {elapsed}s: {len(all_annonces)} brutes -> {len(scored)} retenues")
    return scored
