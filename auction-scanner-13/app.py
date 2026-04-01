"""
Scanner Immobilier Encheres 13 - Departement 13 (Bouches-du-Rhone)
Application web Flask pour scanner les ventes immobilieres aux encheres
dans le departement 13 (Marseille, Aix-en-Provence, etc.)
"""

import os
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from scrapers.interencheres import InterencheresScraper
from scrapers.encheres_publiques import EncheresPubliquesScraper
from scrapers.agorastore import AgorastoreScraper

app = Flask(__name__)

# Cache global des encheres
auction_cache = {
    "data": [],
    "last_update": None,
    "is_scanning": False,
    "errors": []
}

CATEGORIES = {
    "all": "Tous types de biens",
    "appartement": "Appartements",
    "maison": "Maisons & Villas",
    "terrain": "Terrains",
    "local": "Locaux commerciaux",
    "parking": "Parkings & Garages",
    "immeuble": "Immeubles de rapport",
    "autre": "Autre"
}

VILLES_13 = [
    "Marseille", "Aix-en-Provence", "Arles", "Martigues",
    "Aubagne", "Istres", "Salon-de-Provence", "Vitrolles",
    "Marignane", "La Ciotat", "Gardanne", "Les Pennes-Mirabeau",
    "Allauch", "Port-de-Bouc", "Miramas", "Tarascon",
    "Chateaurenard", "Berre-l'Etang", "Plan-de-Cuques",
    "Septemes-les-Vallons", "Trets", "Peyrolles-en-Provence",
    "Bouches-du-Rhone", "13"
]


def get_all_scrapers():
    """Retourne la liste de tous les scrapers disponibles."""
    return [
        InterencheresScraper(),
        EncheresPubliquesScraper(),
        AgorastoreScraper(),
    ]


def run_scan():
    """Execute le scan de toutes les sources d'encheres."""
    global auction_cache

    if auction_cache["is_scanning"]:
        return

    auction_cache["is_scanning"] = True
    auction_cache["errors"] = []
    all_auctions = []

    scrapers = get_all_scrapers()

    for scraper in scrapers:
        try:
            results = scraper.scan(department="13", cities=VILLES_13)
            all_auctions.extend(results)
        except Exception as e:
            error_msg = f"Erreur {scraper.name}: {str(e)}"
            auction_cache["errors"].append(error_msg)
            print(f"[ERREUR] {error_msg}")

    # Tri par date (les plus proches en premier)
    all_auctions.sort(key=lambda x: x.get("date_vente", "9999-12-31"))

    auction_cache["data"] = all_auctions
    auction_cache["last_update"] = datetime.now().isoformat()
    auction_cache["is_scanning"] = False

    print(f"[SCAN] {len(all_auctions)} encheres trouvees - {datetime.now()}")


def background_scanner():
    """Scanner en arriere-plan qui se lance toutes les 30 minutes."""
    while True:
        try:
            run_scan()
        except Exception as e:
            print(f"[ERREUR SCAN] {e}")
        time.sleep(1800)  # 30 minutes


# --- ROUTES ---

@app.route("/")
def index():
    """Page principale du dashboard."""
    return render_template("index.html", categories=CATEGORIES)


@app.route("/api/auctions")
def api_auctions():
    """API: retourne les encheres filtrees."""
    category = request.args.get("category", "all")
    search = request.args.get("search", "").lower()
    price_min = request.args.get("price_min", type=float, default=0)
    price_max = request.args.get("price_max", type=float, default=float("inf"))
    ville = request.args.get("ville", "all").lower()
    sort_by = request.args.get("sort", "date")

    auctions = auction_cache["data"]

    # Filtrage
    filtered = []
    for a in auctions:
        if category != "all" and a.get("category", "autre") != category:
            continue
        if search and search not in a.get("title", "").lower() and search not in a.get("description", "").lower():
            continue
        price = a.get("price_estimate", 0) or 0
        if price < price_min:
            continue
        if price_max != float("inf") and price > price_max:
            continue
        if ville != "all" and ville not in a.get("ville", "").lower():
            continue
        filtered.append(a)

    # Tri
    if sort_by == "price_asc":
        filtered.sort(key=lambda x: x.get("price_estimate", 0) or 0)
    elif sort_by == "price_desc":
        filtered.sort(key=lambda x: x.get("price_estimate", 0) or 0, reverse=True)
    else:
        filtered.sort(key=lambda x: x.get("date_vente", "9999-12-31"))

    return jsonify({
        "auctions": filtered,
        "total": len(filtered),
        "last_update": auction_cache["last_update"],
        "is_scanning": auction_cache["is_scanning"],
        "errors": auction_cache["errors"]
    })


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """API: lance un scan manuel."""
    if auction_cache["is_scanning"]:
        return jsonify({"status": "already_scanning"}), 409

    thread = threading.Thread(target=run_scan, daemon=True)
    thread.start()
    return jsonify({"status": "scan_started"})


@app.route("/api/stats")
def api_stats():
    """API: statistiques du scan."""
    auctions = auction_cache["data"]

    # Stats par categorie
    cat_stats = {}
    for a in auctions:
        cat = a.get("category", "autre")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1

    # Stats par ville
    ville_stats = {}
    for a in auctions:
        v = a.get("ville", "Inconnu")
        ville_stats[v] = ville_stats.get(v, 0) + 1

    # Stats par source
    source_stats = {}
    for a in auctions:
        s = a.get("source", "Inconnu")
        source_stats[s] = source_stats.get(s, 0) + 1

    return jsonify({
        "total": len(auctions),
        "by_category": cat_stats,
        "by_ville": ville_stats,
        "by_source": source_stats,
        "last_update": auction_cache["last_update"]
    })


if __name__ == "__main__":
    # Lancer le scanner en arriere-plan
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()

    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("DEBUG", "false").lower() == "true")
