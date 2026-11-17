#!/usr/bin/env python3
"""Collecte les associations employeuses de PACA depuis l'API Recherche d'entreprises.

L'API (recherche-entreprises.api.gouv.fr) expose SIRENE sans clé. Elle donne pour
chaque association le SIREN, la nature juridique, l'activité, la tranche
d'effectif salarié et l'adresse du siège. Elle ne publie **ni adresse e-mail ni
téléphone** — pas plus que le Répertoire national des associations : ces entrées
arrivent donc sans contact direct, avec un lien vers leur fiche officielle.

Périmètre :
  - associations déclarées, d'insertion, intermédiaires et reconnues d'utilité
    publique (natures juridiques 9220, 9221, 9222, 9230) ;
  - en activité, dont la tranche d'effectif de l'unité légale atteint le seuil
    (50 salariés par défaut) ;
  - dont le **siège** est dans l'un des six départements de PACA. Le filtre
    `region` de l'API retient toute association ayant un établissement dans la
    région : sans ce contrôle, la liste ramène les sièges parisiens des réseaux
    nationaux, dont le décideur n'est pas en PACA.

La tranche d'effectif est celle de l'unité légale entière et date de l'année
indiquée par SIRENE (N-2 en général) : c'est un ordre de grandeur, pas un
effectif à jour. Une association sans tranche renseignée n'apparaît pas.

Usage : python3 annuaires/collecte_associations_paca.py SORTIE.json [SEUIL]
        SEUIL parmi 10, 20, 50, 100, 250 (défaut 50)
"""
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://recherche-entreprises.api.gouv.fr/search"
UA = {"User-Agent": "annuaire-associations-bot/1.0"}
PACA = {"04", "05", "06", "13", "83", "84"}
NATURES = "9220,9221,9222,9230"

# Tranches d'effectif SIRENE, dans l'ordre croissant.
TRANCHES = [
    ("11", 10, "10 à 19 salariés"), ("12", 20, "20 à 49 salariés"),
    ("21", 50, "50 à 99 salariés"), ("22", 100, "100 à 199 salariés"),
    ("31", 200, "200 à 249 salariés"), ("32", 250, "250 à 499 salariés"),
    ("41", 500, "500 à 999 salariés"), ("42", 1000, "1 000 à 1 999 salariés"),
    ("51", 2000, "2 000 à 4 999 salariés"), ("52", 5000, "5 000 à 9 999 salariés"),
    ("53", 10000, "10 000 salariés et plus"),
]
LIBELLE = {code: lib for code, _, lib in TRANCHES}
PLANCHER = {code: n for code, n, _ in TRANCHES}

# Secteur déduit de la division NAF du siège de l'unité légale. La division 94
# (« autres organisations associatives ») est un fourre-tout : elle reste à part.
SECTEURS = [
    (("86",), "Santé"),
    (("87", "88"), "Médico-social et social"),
    (("85",), "Enseignement et formation"),
    (("90", "91", "92", "93"), "Culture, sport et loisirs"),
    (("55", "56"), "Hébergement et restauration"),
    (("78", "81"), "Insertion et services"),
    (("94",), "Autres organisations"),
]


def secteur(naf):
    division = (naf or "")[:2]
    for divisions, libelle in SECTEURS:
        if division in divisions:
            return libelle
    return "Autres activités"


def appeler(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for essai in range(8):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:  # 429 et coupures : on réessaie en espaçant
            time.sleep(1 + essai * 2)
            erreur = e
    sys.exit(f"API injoignable : {erreur}")


def visible(v):
    """SIRENE masque les champs des unités en diffusion partielle."""
    v = (v or "").strip()
    return "" if "NON-DIFFUSIBLE" in v.upper() else v


def collecter(seuil):
    codes = [code for code, n, _ in TRANCHES if n >= seuil]
    sortie, vus, hors_region = [], set(), 0
    # Une requête par tranche : chaque lot reste loin du plafond de 10 000
    # résultats de l'API, et le total annoncé se contrôle tranche par tranche.
    for code in codes:
        page, total_pages = 1, 1
        while page <= total_pages:
            d = appeler({"nature_juridique": NATURES, "region": "93",
                         "etat_administratif": "A", "tranche_effectif_salarie": code,
                         "per_page": 25, "page": page})
            total_pages = d.get("total_pages", 1)
            for r in d.get("results", []):
                siren = r.get("siren")
                if not siren or siren in vus:
                    continue
                vus.add(siren)
                siege = r.get("siege") or {}
                dept = str(siege.get("departement") or "")
                if dept not in PACA:
                    hors_region += 1
                    continue
                tranche = r.get("tranche_effectif_salarie") or code
                nom = visible(r.get("nom_raison_sociale")) or visible(r.get("nom_complet"))
                if not nom:
                    continue
                sigle = visible(r.get("sigle"))
                naf = r.get("activite_principale") or siege.get("activite_principale") or ""
                complements = r.get("complements") or {}
                sortie.append({
                    "siren": siren,
                    "nom": nom,
                    # SIRENE porte souvent « ASS » ou « ASSOCIATION » en guise de sigle.
                    "sigle": sigle if sigle and len(sigle) > 2 and not sigle.upper().startswith("ASS")
                    and sigle.upper() not in nom.upper() else "",
                    "dept": dept,
                    "naf": naf,
                    "secteur": secteur(naf),
                    "tranche": tranche,
                    "effectif": LIBELLE.get(tranche, ""),
                    "plancher": PLANCHER.get(tranche, 0),
                    "annee_effectif": r.get("annee_tranche_effectif_salarie") or "",
                    "adresse": visible(siege.get("adresse")),
                    "commune": visible(siege.get("libelle_commune")),
                    "rna": complements.get("identifiant_association") or "",
                    "rup": r.get("nature_juridique") == "9230",
                    "fiche": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}",
                })
            page += 1
            time.sleep(0.2)
    sortie.sort(key=lambda a: (-a["plancher"], a["dept"], a["nom"]))
    return sortie, hors_region


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    seuil = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    if seuil not in {n for _, n, _ in TRANCHES}:
        sys.exit("SEUIL doit valoir 10, 20, 50, 100 ou 250")
    associations, hors_region = collecter(seuil)
    pathlib.Path(sys.argv[1]).write_text(
        json.dumps(associations, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✅ {len(associations)} associations de {seuil} salariés et plus, siège en PACA")
    print(f"   {hors_region} écartées : établissement en PACA mais siège hors région")
    from collections import Counter
    for cle in ("dept", "secteur", "effectif"):
        print("   " + " · ".join(f"{k} {n}" for k, n in
                                 sorted(Counter(a[cle] for a in associations).items())))


if __name__ == "__main__":
    main()
