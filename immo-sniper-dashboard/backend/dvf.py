"""
Module DVF (Demandes de Valeurs Foncières) — données officielles de transactions immobilières.
Utilise l'API ouverte de data.gouv.fr pour récupérer les prix médians par commune.
"""
import requests
import time
import threading

_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 3600 * 24  # 24h

# Codes INSEE des communes surveillées (dept 13, rayon 30km autour Les Pennes-Mirabeau)
COMMUNES = {
    "13055": "Marseille",
    "13001": "Aix-en-Provence",
    "13054": "Marignane",
    "13119": "Vitrolles",
    "13071": "Les Pennes-Mirabeau",
    "13056": "Martigues",
    "13042": "Gignac-la-Nerthe",
    "13081": "Rognac",
    "13014": "Berre-l'Etang",
    "13028": "Chateauneuf-les-Martigues",
    "13022": "Carry-le-Rouet",
    "13078": "La Ciotat",
    "13047": "Istres",
    "13039": "Gardanne",
    "13117": "Velaux",
    "13032": "Ensuès-la-Redonne",
    "13098": "Sausset-les-Pins",
    "13103": "Septèmes-les-Vallons",
    "13059": "Meyreuil",
    "13015": "Bouc-Bel-Air",
    "13019": "Cabriès",
}

# Mapping code postal -> code INSEE (simplifié)
CP_TO_INSEE = {
    "13127": "13119",  # Vitrolles
    "13700": "13054",  # Marignane
    "13170": "13071",  # Les Pennes-Mirabeau
    "13180": "13042",  # Gignac-la-Nerthe
    "13340": "13081",  # Rognac
    "13130": "13014",  # Berre-l'Etang
    "13220": "13028",  # Chateauneuf-les-Martigues
    "13620": "13022",  # Carry-le-Rouet
    "13500": "13056",  # Martigues
    "13100": "13001",  # Aix-en-Provence
    "13090": "13001",  # Aix-en-Provence
    "13013": "13055",  # Marseille 13e
    "13014": "13055",  # Marseille 14e
    "13015": "13055",  # Marseille 15e
    "13016": "13055",  # Marseille 16e
    "13002": "13055",  # Marseille 2e
    "13003": "13055",  # Marseille 3e
    "13004": "13055",  # Marseille 4e
    "13005": "13055",  # Marseille 5e
    "13006": "13055",  # Marseille 6e
    "13007": "13055",  # Marseille 7e
    "13008": "13055",  # Marseille 8e
    "13009": "13055",  # Marseille 9e
    "13010": "13055",  # Marseille 10e
    "13011": "13055",  # Marseille 11e
    "13012": "13055",  # Marseille 12e
    "13001": "13055",  # Marseille 1er
    "13120": "13039",  # Gardanne
    "13880": "13117",  # Velaux
    "13240": "13103",  # Septèmes-les-Vallons
    "13320": "13015",  # Bouc-Bel-Air
    "13480": "13019",  # Cabriès
    "13600": "13078",  # La Ciotat
    "13800": "13047",  # Istres
    "13960": "13098",  # Sausset-les-Pins
    "13820": "13032",  # Ensuès-la-Redonne
}


def get_dvf_prix_median(code_commune, type_bien="Maison"):
    """Récupère le prix médian au m² pour une commune via l'API DVF."""
    cache_key = f"{code_commune}_{type_bien}"
    with _cache_lock:
        if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < CACHE_TTL:
            return _cache[cache_key]["val"]

    try:
        # API DVF ouverte (data.gouv.fr)
        url = "https://api.cquest.org/dvf"
        params = {
            "code_commune": code_commune,
            "nature_mutation": "Vente",
            "type_local": type_bien,
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        resultats = data.get("resultats", [])
        if not resultats:
            return None

        # Calculer le prix médian au m² sur les transactions récentes
        prix_m2_list = []
        for r in resultats:
            surface = r.get("surface_reelle_bati", 0)
            valeur = r.get("valeur_fonciere", 0)
            if surface and surface > 10 and valeur and valeur > 10000:
                prix_m2_list.append(valeur / surface)

        if not prix_m2_list:
            return None

        prix_m2_list.sort()
        median = prix_m2_list[len(prix_m2_list) // 2]

        with _cache_lock:
            _cache[cache_key] = {"val": round(median), "ts": time.time()}

        return round(median)

    except Exception as e:
        print(f"[DVF] Erreur pour {code_commune}: {e}")
        return None


def get_median_for_cp(code_postal, type_bien="Maison"):
    """Récupère le prix médian pour un code postal."""
    code_insee = CP_TO_INSEE.get(code_postal)
    if not code_insee:
        return None
    return get_dvf_prix_median(code_insee, type_bien)


# Prix médians de secours (DVF 2023) si l'API ne répond pas
FALLBACK_MEDIANS = {
    "13127": {"Maison": 2450, "Terrain": 130, "Appartement": 2200},
    "13700": {"Maison": 2800, "Terrain": 130, "Appartement": 2180},
    "13170": {"Maison": 3100, "Terrain": 200, "Appartement": 2800},
    "13180": {"Maison": 2680, "Terrain": 150, "Appartement": 2400},
    "13340": {"Maison": 2750, "Terrain": 160, "Appartement": 2500},
    "13130": {"Maison": 2100, "Terrain": 100, "Appartement": 1800},
    "13220": {"Maison": 2600, "Terrain": 170, "Appartement": 2300},
    "13620": {"Maison": 3200, "Terrain": 310, "Appartement": 2900},
    "13500": {"Maison": 2050, "Terrain": 120, "Appartement": 1900},
    "13100": {"Maison": 3450, "Terrain": 250, "Appartement": 3200},
    "13014": {"Maison": 2200, "Terrain": 100, "Appartement": 1800},
    "13002": {"Maison": 2800, "Terrain": 1000, "Appartement": 2600},
    "13003": {"Maison": 2400, "Terrain": 800, "Appartement": 2100},
    "13008": {"Maison": 3500, "Terrain": 500, "Appartement": 3200},
    "13013": {"Maison": 2600, "Terrain": 200, "Appartement": 2300},
}


def get_median_with_fallback(code_postal, type_bien="Maison"):
    """Tente l'API DVF, sinon utilise les données de secours."""
    result = get_median_for_cp(code_postal, type_bien)
    if result:
        return result
    fb = FALLBACK_MEDIANS.get(code_postal, {})
    return fb.get(type_bien, fb.get("Maison", 2500))
