#!/usr/bin/env python3
"""Collecte les dirigeants déclarés (président, directeur général) par SIREN.

Source : API Recherche d'entreprises, qui relaie le Registre national des
entreprises. Elle couvre les sociétés (SA d'HLM, Sem, Spl) ; les associations et
les établissements publics n'y déclarent en général personne. Les directeurs
financiers n'y figurent jamais : ce ne sont pas des mandataires sociaux.

Usage : python3 annuaires/collecte_dirigeants.py SIRENS.json SORTIE.json
        SIRENS.json : {clé: siren}
"""
import json
import pathlib
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

RETENUS = ("président", "president", "directeur général", "directeur general", "gérant", "gerant",
           "directeur", "maire")
ECARTES = ("commissaire", "administrateur", "membre", "censeur", "suppléant", "suppleant")


def dirigeants(siren):
    url = f"https://recherche-entreprises.api.gouv.fr/search?q={siren}&per_page=1"
    for essai in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "annuaire-paca-bot/1.0"})
            d = json.loads(urllib.request.urlopen(req, timeout=30).read())
            break
        except Exception:
            time.sleep(1 + essai)
    else:
        return []
    for r in d.get("results", []):
        if r.get("siren") != siren:
            continue
        sortie = []
        for p in r.get("dirigeants") or []:
            qualite = (p.get("qualite") or "").strip()
            q = qualite.lower()
            if p.get("type_dirigeant") != "personne physique" or not any(x in q for x in RETENUS) \
                    or any(x in q for x in ECARTES):
                continue
            prenom = (p.get("prenoms") or "").split(" ")[0].split(",")[0].title()
            nom = (p.get("nom") or "").upper()
            if nom:
                sortie.append((qualite, f"{prenom} {nom}".strip()))
        return sortie
    return []


def main():
    sirens = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    cles = [k for k, s in sirens.items() if s]
    resultat = {}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for cle, liste in zip(cles, pool.map(dirigeants, [sirens[k] for k in cles])):
            if liste:
                resultat[cle] = liste
    pathlib.Path(sys.argv[2]).write_text(json.dumps(resultat, ensure_ascii=False, indent=1) + "\n",
                                         encoding="utf-8")
    print(f"✅ {len(resultat)} organismes avec au moins un dirigeant déclaré, sur {len(cles)}")


if __name__ == "__main__":
    main()
