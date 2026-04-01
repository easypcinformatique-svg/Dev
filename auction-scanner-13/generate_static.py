#!/usr/bin/env python3
"""
Generateur de site statique pour le Scanner Encheres 13.
Scrape les sources, genere un fichier JSON de donnees,
et copie le site statique dans docs/.
"""

import json
import os
import sys
from datetime import datetime

# Ajouter le repertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.interencheres import InterencheresScraper
from scrapers.encheres_publiques import EncheresPubliquesScraper
from scrapers.agorastore import AgorastoreScraper


def generate():
    """Genere les donnees et le site statique."""
    print("[*] Scanner Encheres 13 - Generation statique")

    # Scraper les donnees
    all_auctions = []
    scrapers = [
        InterencheresScraper(),
        EncheresPubliquesScraper(),
        AgorastoreScraper(),
    ]

    for scraper in scrapers:
        try:
            results = scraper.scan(department="13")
            all_auctions.extend(results)
            print(f"  [OK] {scraper.name}: {len(results)} encheres")
        except Exception as e:
            print(f"  [ERR] {scraper.name}: {e}")

    all_auctions.sort(key=lambda x: x.get("date_vente", "9999-12-31"))

    # Stats
    cat_stats = {}
    ville_stats = {}
    source_stats = {}
    for a in all_auctions:
        cat = a.get("category", "autre")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1
        v = a.get("ville", "Inconnu")
        ville_stats[v] = ville_stats.get(v, 0) + 1
        s = a.get("source", "Inconnu")
        source_stats[s] = source_stats.get(s, 0) + 1

    data = {
        "auctions": all_auctions,
        "stats": {
            "total": len(all_auctions),
            "by_category": cat_stats,
            "by_ville": ville_stats,
            "by_source": source_stats,
        },
        "generated_at": datetime.now().isoformat(),
    }

    # Ecrire le JSON
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(docs_dir, exist_ok=True)

    data_path = os.path.join(docs_dir, "data.json")
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] {len(all_auctions)} encheres generees -> docs/data.json")
    print(f"[OK] Derniere mise a jour: {data['generated_at']}")


if __name__ == "__main__":
    generate()
