#!/usr/bin/env python3
"""Assemble `dirigeants.json` : président, directeur général et directeur financier.

Sources, toutes publiques :
  - Registre national des entreprises, via l'API Recherche d'entreprises
    (`collecte_dirigeants.py`) : président et directeur général des sociétés
    (SA d'HLM, Sem, Spl) et de quelques offices ;
  - BANATIC : président des syndicats et des EPCI ;
  - le site de l'organisme, quand il publie son équipe de direction : c'est la
    seule source des directeurs et responsables financiers, qui ne sont pas des
    mandataires sociaux et ne figurent dans aucun registre.

Les maires viennent directement de l'annuaire des maires, dans
`build_prospection.py`. Aucun nom n'est tiré d'un réseau social.

Usage : python3 annuaires/assemble_dirigeants.py CACHE
  CACHE contient dirigeants_api.json, fonctions_sites.json, banatic_paca.json
"""
import json
import pathlib
import re
import sys
import unicodedata

SORTIE = pathlib.Path(__file__).resolve().parent / "dirigeants.json"
RACINE = pathlib.Path(__file__).resolve().parent.parent
PAGE = RACINE / "annuaire-prospection-paca.html"
ORDRE = ["Président", "PDG", "DG", "DG délégué", "DGS", "Directeur", "DAF", "Dir. publication"]
FAUX_NOMS = {"DECOUVRIR", "VOIR", "CONTACTER", "LIRE", "EN", "NOTRE", "SAINT", "SAINTE", "LOI",
             "AMICALE", "INFORMATIQUE", "NOTRE", "LYCEE", "COLLEGE", "ECOLE"}
GENERIQUES = {"COMMUNAUTE", "AGGLOMERATION", "COMMUNES", "METROPOLE", "CA", "CC", "METRO", "DE",
              "DU", "DES", "LA", "LE", "LES", "D", "L", "ET", "PAYS", "AGGLO"}


def norme(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def role(qualite):
    q = norme(qualite)
    if "VICE" in q:
        return ""
    if "PRESIDENT" in q and "DIRECTEUR GENERAL" in q:
        return "PDG"
    if "DELEGUE" in q:
        return "DG délégué"
    if "PRESIDENT" in q:
        return "Président"
    if "DIRECTEUR" in q or "GERANT" in q:
        return "DG"
    return ""


def main():
    cache = pathlib.Path(sys.argv[1])
    fiches = {}

    def poser(cle, r, nom):
        site = nom.endswith(" (site)")
        nom = re.sub(r"\s*\((?!site\))[^)]*\)", "", nom).strip()
        if r and nom and norme(nom).split()[0] not in FAUX_NOMS:
            fiches.setdefault(cle, {}).setdefault(r, nom)

    for cle, liste in json.loads((cache / "dirigeants_api.json").read_text(encoding="utf-8")).items():
        for qualite, nom in liste:
            poser(cle, role(qualite), nom)

    banatic = json.loads((cache / "banatic_paca.json").read_text(encoding="utf-8"))
    for g in banatic:
        poser(f'nom:{norme(g["nom"])}|{g["dept"]}', "Président", g["president"])
    # Les EPCI de la page portent le libellé de l'annuaire de l'administration
    # (« Communauté de communes - Sisteronais Buëch ») : rapprochement par mots.
    epci = [g for g in banatic if g["nature"] in ("CC", "CA", "METRO", "CU")]
    bloc = re.search(r"const DATA = \[\n([\s\S]*?)\n\];", PAGE.read_text(encoding="utf-8")).group(1)
    for ligne in bloc.splitlines():
        e = dict(re.findall(r'(\w+):"([^"]*)"', ligne))
        if e.get("type") != "EPCI":
            continue
        mots = set(norme(e["nom"]).split()) - GENERIQUES
        meilleurs = sorted(((len(mots & (set(norme(g["nom"]).split()) - GENERIQUES))
                             / max(1, len(mots | (set(norme(g["nom"]).split()) - GENERIQUES))), g)
                            for g in epci if g["dept"] == e["dept"]), key=lambda x: -x[0])
        if meilleurs and meilleurs[0][0] >= 0.6:
            poser(f'nom:{norme(e["nom"])}|{e["dept"]}', "Président", meilleurs[0][1]["president"])

    # Départements et Région : annuaire de l'administration (DILA), qui nomme le
    # président, le directeur général des services et parfois le directeur des finances.
    personnes = cache / "dila_personnes.json"
    if personnes.exists():
        depts = {e["nom"]: e["dept"] for e in
                 (dict(re.findall(r'(\w+):"([^"]*)"', l)) for l in bloc.splitlines())
                 if e.get("type") in ("Département", "Région")}
        for nom, liste in json.loads(personnes.read_text(encoding="utf-8")).items():
            if nom not in depts:
                continue
            cle = f'nom:{norme(nom)}|{depts[nom]}'
            for fonction, personne in liste:
                f = norme(fonction)
                if f.startswith("PRESIDENT"):
                    poser(cle, "Président", personne)
                elif "DIRECT" in f and "GENERAL" in f and "SERVICES" in f and "ADJOINT" not in f:
                    poser(cle, "DGS", personne)
                elif "FINANCE" in f:
                    poser(cle, "DAF", personne)

    # Sites des organismes : seulement à défaut d'une source officielle, jamais
    # pour les communes (le maire fait foi), et pas quand plusieurs organismes
    # partagent le même site — le nom relevé y serait celui de la collectivité mère.
    sites = cache / "fonctions_sites.json"
    if sites.exists():
        contacts = json.loads((pathlib.Path(__file__).resolve().parent
                               / "contacts_complementaires.json").read_text(encoding="utf-8"))
        partage = {}
        for k, v in contacts.items():
            if v.get("web"):
                partage[v["web"]] = partage.get(v["web"], 0) + 1
        communes = {f'nom:{norme(e["nom"])}|{e["dept"]}' for e in
                    (dict(re.findall(r'(\w+):"([^"]*)"', l)) for l in bloc.splitlines())
                    if e.get("type") == "Commune"}
        for cle, f in json.loads(sites.read_text(encoding="utf-8")).items():
            if cle in communes or partage.get(contacts.get(cle, {}).get("web", ""), 0) > 1:
                continue
            officiel = fiches.get(cle, {})
            for r in ("Président", "DG", "Directeur", "DAF", "Dir. publication"):
                if r not in f:
                    continue
                nom = f[r] if isinstance(f[r], str) else f[r][0]
                if r == "Président" and ("Président" in officiel or "PDG" in officiel):
                    continue
                if r in ("DG", "Directeur") and any(x in officiel for x in ("DG", "PDG", "DGS")):
                    continue
                if r == "Dir. publication" and (officiel or any(x in f for x in ("Président", "DG", "Directeur"))):
                    continue
                poser(cle, r, nom + " (site)")

    sortie = {cle: " · ".join(f"{r} : {f[r]}" for r in ORDRE if r in f)
              for cle, f in sorted(fiches.items())}
    SORTIE.write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✅ {SORTIE.name} — {len(sortie)} organismes, "
          f"{sum('DAF' in v for v in sortie.values())} avec un directeur financier")


if __name__ == "__main__":
    main()
