#!/usr/bin/env python3
"""Régénère annuaire-maires-france.html pour PACA + Monaco.

Sources, toutes officielles :
  - populations  : INSEE, populations de référence 2023 (décret du 26/12/2025,
                   en vigueur au 1er janvier 2026) — fichier d'ensemble
  - maires       : RNE (data.gouv.fr), audité contre les résultats officiels
                   du second tour des municipales 2026
  - coordonnées  : Annuaire de l'administration (DILA), service-public.fr
  - Monaco       : recensement IMSEE 2023 et site officiel de la Mairie

Les données restent dans le tableau `let DATA = [ … ];` que
.github/workflows/update-maires.yml relit et réécrit chaque semaine, avec ses
huit clés dans l'ordre imposé : ville, pop, dept, region, maire, adresse, tel,
email. Toute clé supplémentaire serait perdue à la première mise à jour.

Usage : python3 annuaires/build_maires_paca.py [--cache RÉPERTOIRE]
"""
import argparse
import csv
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "annuaire-maires-france.html"
SEUIL = 30000

DEPTS = {"04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes",
         "13": "Bouches-du-Rhône", "83": "Var", "84": "Vaucluse", "MC": "Monaco"}
REGION = "Provence-Alpes-Côte d'Azur"
ARRONDISSEMENT = re.compile(r"^(Paris|Lyon|Marseille)\s+\d+\w*\s+Arrondissement$", re.I)

# Marseille est absente de la feuille « Communes » d'INSEE, qui ne liste que ses
# arrondissements municipaux ; sa population est la somme de ceux-ci.
MARSEILLE = {"code": "13055", "nom": "Marseille", "dep": "13"}

# Monaco n'est pas une commune française : aucune source française ne la couvre.
MONACO = {
    "ville": "Monaco", "pop": 38367,          # recensement IMSEE au 31/12/2023
    "dept": "MC", "region": "Monaco",
    "maire": "Georges Marsan",
    "adresse": "Place de la Mairie, 98000 Monaco",
    "tel": "+377 93 15 28 63",
    "email": "",                               # non publié sur mairie.mc/contacts
}

CLES = ["ville", "pop", "dept", "region", "maire", "adresse", "tel", "email"]


def sans_accents(s):
    s = unicodedata.normalize("NFD", str(s))
    return re.sub(r"[̀-ͯ]", "", s).upper().strip()


def titre(s):
    petits = {"de", "du", "des", "le", "la", "les", "l", "d", "en", "sur", "sous", "et"}
    morceaux = re.split(r"([-\s'])", str(s).lower())
    return "".join(m.capitalize() if (i == 0 or m not in petits) else m
                   for i, m in enumerate(morceaux))


def propre(v):
    """Valeur utilisable dans une chaîne JS délimitée par des guillemets doubles.

    Les regex de relecture du workflow capturent avec [^"]* et json.loads refuse
    l'échappement \\' : on retire les antislashs et on convertit les guillemets.
    """
    return re.sub(r"\s+", " ", str(v or "").replace("\\", "").replace('"', "'")).strip()


def communes_insee(cache):
    import openpyxl
    wb = openpyxl.load_workbook(cache / "insee_pop2023.xlsx", read_only=True)
    lignes = list(wb["Communes"].iter_rows(values_only=True))[8:]
    retenues, marseille = [], 0
    for r in lignes:
        if not r or not r[6]:
            continue
        nom, dep, pop = str(r[6]).strip(), str(r[2]), int(r[7])
        if ARRONDISSEMENT.match(nom):
            if nom.lower().startswith("marseille"):
                marseille += pop
            continue
        if dep in DEPTS and pop > SEUIL:
            retenues.append({"code": dep[:2] + str(r[5]).zfill(3), "nom": nom,
                             "dep": dep, "pop": pop})
    if marseille:
        retenues.append({**MARSEILLE, "pop": marseille})
    return sorted(retenues, key=lambda c: -c["pop"])


def maires_rne(cache):
    """Maire par (nom de commune sans accents, code département)."""
    texte = (cache / "elus-maire.csv").read_text(encoding="utf-8", errors="replace")
    table = {}
    for row in csv.DictReader(texte.splitlines(), delimiter=";"):
        commune = row.get("Libellé de la commune", "").strip()
        nom, prenom = row.get("Nom de l'élu", "").strip(), row.get("Prénom de l'élu", "").strip()
        dep = row.get("Code du département", "").strip()
        if commune and nom:
            complet = f"{titre(prenom)} {titre(nom)}" if prenom else titre(nom)
            table[(sans_accents(commune), dep)] = complet
    return table


def gagnants_second_tour(cache):
    """Candidat arrivé en tête au second tour, par (commune, département).

    Même lecture que l'étape d'audit du workflow : les colonnes de candidats se
    répètent tous les 13 champs à partir du 19e.
    """
    texte = (cache / "t2.csv").read_text(encoding="utf-8-sig", errors="replace")
    lecteur = csv.reader(texte.splitlines(), delimiter=";")
    next(lecteur, None)
    gagnants = {}
    for row in lecteur:
        row = [c.strip().strip('"') for c in row]
        if len(row) < 26:
            continue
        dep, commune = row[0], row[3]
        meilleur_nom = meilleur_prenom = ""
        meilleur_voix = -1
        i = 18
        while i + 7 < len(row):
            nom = row[i + 1]
            if not nom and not row[i + 5]:
                break
            try:
                voix = int(row[i + 7].replace(" ", "").replace("%", ""))
            except ValueError:
                voix = 0
            if voix > meilleur_voix:
                meilleur_voix, meilleur_nom, meilleur_prenom = voix, nom, row[i + 2]
            i += 13
        if meilleur_voix > 0 and meilleur_nom:
            complet = (f"{titre(meilleur_prenom)} {titre(meilleur_nom)}"
                       if meilleur_prenom else titre(meilleur_nom))
            gagnants[(sans_accents(commune), dep)] = complet
    return gagnants


def coordonnees(cache):
    """Adresse, téléphone et courriel de chaque mairie, par code INSEE."""
    brut = json.loads((cache / "mairies.json").read_text(encoding="utf-8"))
    table = {}
    for code, rec in brut.items():
        adresses = rec.get("adresse")
        if isinstance(adresses, str):
            adresses = json.loads(adresses)
        postale = next((a for a in (adresses or []) if a.get("type_adresse") == "Adresse"),
                       (adresses or [{}])[0] if adresses else {})
        voie = ", ".join(x for x in (postale.get("complement1"), postale.get("complement2"),
                                     postale.get("numero_voie")) if x)
        ville = " ".join(x for x in (postale.get("code_postal"),
                                     postale.get("nom_commune")) if x)
        tels = rec.get("telephone")
        if isinstance(tels, str):
            tels = json.loads(tels)
        table[code] = {
            "adresse": ", ".join(x for x in (voie, ville) if x),
            "tel": (tels[0].get("valeur", "") if tels else ""),
            "email": rec.get("adresse_courriel") or "",
        }
    return table


def construire(cache):
    communes = communes_insee(cache)
    rne = maires_rne(cache)
    t2 = gagnants_second_tour(cache)
    contacts = coordonnees(cache)

    entrees, sans_maire, audites = [], [], []
    for c in communes:
        cle = (sans_accents(c["nom"]), c["dep"])
        maire = rne.get(cle, "")
        officiel = t2.get(cle)
        if officiel and sans_accents(officiel) != sans_accents(maire):
            audites.append((c["nom"], maire, officiel))
            maire = officiel
        if not maire:
            sans_maire.append(f"{c['nom']} ({c['dep']})")
        contact = contacts.get(c["code"], {})
        entrees.append({"ville": c["nom"], "pop": c["pop"], "dept": c["dep"],
                        "region": REGION, "maire": maire,
                        "adresse": contact.get("adresse", ""),
                        "tel": contact.get("tel", ""),
                        "email": contact.get("email", "")})
    entrees.append(dict(MONACO))
    entrees.sort(key=lambda e: -e["pop"])
    return entrees, sans_maire, audites


def bloc_data(entrees):
    lignes = []
    for e in entrees:
        parts = [f"{k}:{e[k]}" if k == "pop" else f'{k}:"{propre(e[k])}"' for k in CLES]
        lignes.append("  {" + ",".join(parts) + "}")
    return "let DATA = [\n" + ",\n".join(lignes) + "\n];"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None,
                    help="répertoire des fichiers sources téléchargés")
    args = ap.parse_args()
    cache = pathlib.Path(args.cache) if args.cache else ROOT / "annuaires" / "cache"
    if not (cache / "insee_pop2023.xlsx").exists():
        sys.exit(f"sources introuvables dans {cache} — voir annuaires/README.md")

    entrees, sans_maire, audites = construire(cache)
    html = PAGE.read_text(encoding="utf-8")
    nouveau, n = re.subn(r"let DATA = \[[\s\S]*?\];", lambda _: bloc_data(entrees), html, count=1)
    if n != 1:
        sys.exit("bloc DATA introuvable dans la page")
    PAGE.write_text(nouveau, encoding="utf-8")

    print(f"✅ {len(entrees)} entrées ({len(entrees)-1} communes PACA + Monaco)")
    print(f"   maires renseignés : {sum(1 for e in entrees if e['maire'])}")
    print(f"   adresses          : {sum(1 for e in entrees if e['adresse'])}")
    print(f"   téléphones        : {sum(1 for e in entrees if e['tel'])}")
    print(f"   courriels         : {sum(1 for e in entrees if e['email'])}")
    if audites:
        print(f"   corrigés par l'audit second tour : {len(audites)}")
        for ville, avant, apres in audites:
            print(f"     {ville} : {avant or '(vide)'} → {apres}")
    if sans_maire:
        print(f"   ⚠ sans maire : {', '.join(sans_maire)}")


if __name__ == "__main__":
    main()
