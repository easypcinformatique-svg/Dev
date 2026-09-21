#!/usr/bin/env python3
"""Assemble la page de prospection PACA à partir des annuaires déjà publiés.

Réunit dans un seul fichier, avec un filtre « type d'organisme » :
  - les communes de PACA et Monaco      (annuaire-maires-france.html)
  - les entreprises publiques locales   (annuaire-sem-spl-syndicats.html)
  - les EPCI, départements et Région    (collecte_organismes_paca.py)
  - les syndicats et bailleurs sociaux  (BANATIC, quand le fichier est là)

Les deux annuaires restent la source de vérité pour ce qu'ils contiennent : la
page de prospection les relit plutôt que de dupliquer leurs données, pour qu'une
mise à jour hebdomadaire s'y propage à la régénération suivante.

Usage : python3 annuaires/build_prospection.py [--organismes X.json] [--banatic Y.csv]
"""
import argparse
import csv
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
MAIRES = RACINE / "annuaire-maires-france.html"
EPL = RACINE / "annuaire-sem-spl-syndicats.html"
GABARIT = pathlib.Path(__file__).resolve().parent / "template_prospection.html"
SORTIE = RACINE / "annuaire-prospection-paca.html"

DEPTS = {"04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes",
         "13": "Bouches-du-Rhône", "83": "Var", "84": "Vaucluse", "MC": "Monaco"}

# Natures juridiques BANATIC retenues : celles qui empruntent. Les syndicats de
# communes et mixtes portent des projets d'eau, d'assainissement, d'énergie ou
# de transport, donc de la dette ; les autres formes sont écartées.
NATURES_RETENUES = re.compile(r"(SIVU|SIVOM|syndicat mixte|SMF|SMO|pôle métropolitain)", re.I)

CLES = ["type", "nom", "dept", "taille", "adresse", "tel", "email", "contact"]


def propre(v):
    """Valeur sûre dans une chaîne JS délimitée par des guillemets doubles."""
    return re.sub(r"\s+", " ", str(v or "").replace("\\", "").replace('"', "'")).strip()


def lire_data(chemin):
    """Extrait le tableau DATA d'une page d'annuaire."""
    html = chemin.read_text(encoding="utf-8")
    bloc = re.search(r"let DATA = (\[[\s\S]*?\]);", html)
    if not bloc:
        sys.exit(f"tableau DATA introuvable dans {chemin.name}")
    texte = re.sub(r"/\*[\s\S]*?\*/", "", bloc.group(1))
    texte = re.sub(r"(\{|,)\s*(\w+)\s*:", r'\1"\2":', texte)
    return json.loads(texte)


def depuis_communes():
    for c in lire_data(MAIRES):
        yield {"type": "Commune", "nom": c["ville"], "dept": c["dept"],
               "taille": f'{c["pop"]:,}'.replace(",", " ") + " hab.",
               "adresse": c["adresse"], "tel": c["tel"],
               "email": c["email"], "contact": c.get("contact", "")}


def depuis_epl():
    for e in lire_data(EPL):
        ca = e.get("ca") or 0
        taille = (f"{ca/1e6:.1f} M€ de CA".replace(".", ",") if ca >= 1e6
                  else f"{round(ca/1000)} k€ de CA" if ca else "")
        yield {"type": f'Epl · {e["regime"]}', "nom": e["nom"], "dept": e["depcode"],
               "taille": taille, "adresse": ", ".join(
                   x for x in (e["adresse"], f'{e["cp"]} {e["ville"]}'.strip()) if x),
               "tel": e["tel"], "email": e["email"], "contact": e.get("web", "")}


def depuis_organismes(chemin):
    if not chemin or not chemin.exists():
        return
    for o in json.loads(chemin.read_text(encoding="utf-8")):
        yield {"type": o["type"], "nom": o["nom"], "dept": o["dept"], "taille": "",
               "adresse": o["adresse"], "tel": o["tel"],
               "email": o["email"], "contact": o["contact"]}


def depuis_banatic(chemin):
    """Syndicats et groupements BANATIC situés en PACA.

    Le fichier couvre la France entière ; le rattachement se fait par le
    département du siège. Les EPCI à fiscalité propre y figurent aussi mais
    sont déjà collectés avec leurs adresses : on ne garde ici que ce que
    l'annuaire de l'administration ne couvre pas.
    """
    if not chemin or not chemin.exists():
        return
    texte = chemin.read_text(encoding="utf-8", errors="replace")
    separateur = ";" if texte[:2000].count(";") > texte[:2000].count(",") else ","
    for ligne in csv.DictReader(texte.splitlines(), delimiter=separateur):
        colonnes = {k.lower().strip(): (v or "").strip() for k, v in ligne.items() if k}
        nature = colonnes.get("nature juridique") or colonnes.get("nature_juridique") or ""
        if not NATURES_RETENUES.search(nature):
            continue
        dept = (colonnes.get("département siège") or colonnes.get("departement")
                or colonnes.get("dept") or "")[:2]
        if dept not in DEPTS:
            continue
        nom = colonnes.get("nom du groupement") or colonnes.get("raison sociale") or ""
        if not nom:
            continue
        yield {"type": f"Syndicat · {nature}", "nom": nom, "dept": dept, "taille": "",
               "adresse": " ".join(x for x in (colonnes.get("adresse", ""),
                                               colonnes.get("code postal", ""),
                                               colonnes.get("ville", "")) if x),
               "tel": colonnes.get("téléphone", "") or colonnes.get("telephone", ""),
               "email": colonnes.get("mél", "") or colonnes.get("mel", "")
                        or colonnes.get("courriel", ""),
               "contact": colonnes.get("site internet", "")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--organismes", default=None)
    ap.add_argument("--banatic", default=None)
    args = ap.parse_args()

    entrees = list(depuis_communes()) + list(depuis_epl())
    entrees += list(depuis_organismes(pathlib.Path(args.organismes) if args.organismes else None))
    entrees += list(depuis_banatic(pathlib.Path(args.banatic) if args.banatic else None))

    # Un organisme peut figurer dans deux sources : on garde la mieux renseignée.
    unique = {}
    for e in entrees:
        cle = (propre(e["nom"]).upper(), e["dept"])
        garde = unique.get(cle)
        if not garde or (bool(e["email"]), bool(e["tel"])) > (bool(garde["email"]), bool(garde["tel"])):
            unique[cle] = e
    entrees = sorted(unique.values(), key=lambda e: (e["type"], e["dept"], e["nom"]))

    lignes = []
    for e in entrees:
        lignes.append("  {" + ",".join(f'{k}:"{propre(e[k])}"' for k in CLES) + "}")
    bloc = "const DATA = [\n" + ",\n".join(lignes) + "\n];"

    types = sorted({e["type"] for e in entrees})
    depts = sorted({e["dept"] for e in entrees}, key=lambda d: (d == "MC", d))
    from datetime import datetime
    maintenant = datetime.now()

    html = GABARIT.read_text(encoding="utf-8")
    for cle, valeur in {
        "__DATA__": bloc,
        "__TYPES__": json.dumps(types, ensure_ascii=False),
        "__DEPTS__": json.dumps({d: DEPTS[d] for d in depts}, ensure_ascii=False),
        "__COUNT__": str(len(entrees)),
        "__VERSION__": f"v.{maintenant.year}.{maintenant.month:02d}.{maintenant.day:02d}"
                       f"-{maintenant.hour:02d}h{maintenant.minute:02d}",
        "__EXPORT_DATE__": maintenant.strftime("%d/%m/%Y"),
    }.items():
        html = html.replace(cle, valeur)
    restes = set(re.findall(r"__[A-Z_]+__", html))
    if restes:
        sys.exit(f"placeholders non substitués : {sorted(restes)}")
    SORTIE.write_text(html, encoding="utf-8")

    avec = sum(1 for e in entrees if e["email"])
    print(f"✅ {SORTIE.name} — {len(entrees)} organismes, {avec} avec une adresse")
    from collections import Counter
    for t, n in sorted(Counter(e["type"] for e in entrees).items()):
        m = sum(1 for e in entrees if e["type"] == t and e["email"])
        print(f"   {t:<28} {n:>4}  dont {m:>3} avec adresse")


if __name__ == "__main__":
    main()
