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

# Types BANATIC retenus : les syndicats et pôles. Les communautés de communes,
# d'agglomération et métropoles en sont exclues — elles sont déjà collectées
# depuis l'annuaire de l'administration, qui donne en plus leurs adresses.
TYPES_SYNDICAT = {"SIVU", "SIVOM", "SMF", "SMO", "PETR", "POLEM"}

# Seuil de population desservie sous lequel un syndicat est écarté. En PACA, 58
# des 251 syndicats passent dessous : des SIVU d'école ou d'eau entre deux
# communes, dont les emprunts se comptent en dizaines de milliers d'euros. Un
# syndicat à faible population mais à nombreux membres est conservé : la
# population attribuée à un syndicat d'ingénierie ne reflète pas son activité.
SEUIL_POPULATION = 5000
SEUIL_MEMBRES = 5

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


def depuis_banatic(chemin, ecartes=None):
    """Syndicats de PACA, depuis BANATIC via le portail OpenDataSoft public.

    BANATIC ne publie ni adresse e-mail ni téléphone : ces entrées arrivent donc
    avec le nom, le type, le président, la commune de siège et la population
    desservie, mais sans contact direct. C'est une limite de la source, pas une
    collecte incomplète.

    Les EPCI à fiscalité propre y figurent aussi et sont ignorés ici : ils sont
    déjà collectés depuis l'annuaire de l'administration, avec leurs adresses.
    Les deux sources en comptent 52 de part et d'autre, ce qui les recoupe.
    """
    if not chemin or not chemin.exists():
        return
    for r in json.loads(chemin.read_text(encoding="utf-8")):
        if r.get("legal_type_code") not in TYPES_SYNDICAT:
            continue
        dept = str(r.get("dep_code_office") or "")
        nom = (r.get("intercommunalite_name") or "").strip()
        if dept not in DEPTS or not nom:
            continue
        population = r.get("intercommunalite_pop_tot") or 0
        membres = r.get("member_count") or 0
        if population < SEUIL_POPULATION and membres < SEUIL_MEMBRES:
            if ecartes is not None:
                ecartes.append(nom)
            continue
        president = " ".join(x for x in (r.get("president_firstname"),
                                         r.get("president_lastname")) if x).strip()
        taille = f'{population:,}'.replace(",", " ") + " hab. desservis" if population else ""
        siege = (r.get("com_name_office") or "").strip()
        yield {"type": f'Syndicat · {r.get("legal_type_code")}', "nom": nom, "dept": dept,
               "taille": taille,
               "adresse": f"Siège : {siege}" + (f" — président {president}" if president else ""),
               "tel": "", "email": "", "contact": ""}


def depuis_bailleurs(chemin):
    """Bailleurs sociaux de PACA, depuis SIRENE via le portail OpenDataSoft public.

    SIRENE ne marque pas les organismes de logement social : le repérage croise
    l'activité (location de logements) et la catégorie juridique (office public
    de l'habitat, SA et coopératives de HLM). La catégorie « autre SA » est
    volontairement exclue — avec la seule activité, elle ramenait 741 « bailleurs »
    dont des SCI nommées COUCOU ou BACCARA.

    La liste qui fait foi est le répertoire des organismes de logement social du
    ministère, qui n'est pas en accès ouvert : quelques SA bailleurs dont la
    forme juridique ne mentionne ni HLM ni habitat peuvent manquer.
    """
    if not chemin or not chemin.exists():
        return
    for r in json.loads(chemin.read_text(encoding="utf-8")):
        dept = str(r.get("codedepartementetablissement") or "")
        nom = (r.get("denominationunitelegale") or "").strip()
        if dept not in DEPTS or not nom:
            continue
        adresse = " ".join(x for x in (r.get("adresseetablissement"),
                                       r.get("codepostaletablissement"),
                                       r.get("libellecommuneetablissement")) if x)
        yield {"type": "Bailleur social", "nom": nom, "dept": dept, "taille": "",
               "adresse": adresse, "tel": "", "email": "", "contact": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--organismes", default=None)
    ap.add_argument("--banatic", default=None)
    ap.add_argument("--bailleurs", default=None)
    args = ap.parse_args()

    entrees = list(depuis_communes()) + list(depuis_epl())
    entrees += list(depuis_organismes(pathlib.Path(args.organismes) if args.organismes else None))
    ecartes = []
    entrees += list(depuis_banatic(pathlib.Path(args.banatic) if args.banatic else None,
                                   ecartes))
    entrees += list(depuis_bailleurs(pathlib.Path(args.bailleurs) if args.bailleurs else None))

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
    if ecartes:
        print(f"   {len(ecartes)} syndicats écartés (moins de {SEUIL_POPULATION} hab. "
              f"desservis et moins de {SEUIL_MEMBRES} membres)")
    from collections import Counter
    for t, n in sorted(Counter(e["type"] for e in entrees).items()):
        m = sum(1 for e in entrees if e["type"] == t and e["email"])
        print(f"   {t:<28} {n:>4}  dont {m:>3} avec adresse")


if __name__ == "__main__":
    main()
