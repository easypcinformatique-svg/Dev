#!/usr/bin/env python3
"""Collecte les organismes publics de PACA depuis l'annuaire de l'administration.

Couvre les EPCI à fiscalité propre, les conseils départementaux et le conseil
régional. L'annuaire (DILA) donne pour chacun le SIREN, l'adresse, le téléphone,
le site et — contrairement aux communes — souvent l'adresse e-mail.

Les syndicats et les bailleurs sociaux n'y figurent pas : ils relèvent d'une
autre source (API entreprises filtrée par nature juridique), traitée à part.

Le rattachement à PACA se fait par le code INSEE de la commune de siège, seul
champ géographique fiable de l'annuaire : son département doit être l'un des six.

Usage : python3 annuaires/collecte_organismes_paca.py SORTIE.json
"""
import json
import pathlib
import sys
import time
import urllib.parse
import urllib.request

BASE = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/catalog/datasets/"
        "api-lannuaire-administration/records")
CHAMPS = ("nom,siren,adresse,telephone,adresse_courriel,formulaire_contact,"
          "site_internet,code_insee_commune,pivot")
UA = {"User-Agent": "annuaire-organismes-bot/1.0"}
PACA = {"04", "05", "06", "13", "83", "84"}

# (libellé affiché, clause de sélection dans l'annuaire)
FAMILLES = [
    ("EPCI",         'pivot LIKE "epci"'),
    ("Département",  'nom LIKE "Conseil départemental"'),
    ("Région",       'nom LIKE "Conseil régional"'),
]


def recupere(url, essais=10):
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(min(2 * (i + 1), 12))
    return None


def deplie(valeur):
    """Les champs composés arrivent tantôt en JSON, tantôt déjà décodés."""
    if isinstance(valeur, str):
        try:
            return json.loads(valeur)
        except json.JSONDecodeError:
            return []
    return valeur or []


def departement(code_insee):
    code = str(code_insee or "")
    if code.startswith("97") or code.startswith("98"):
        return code[:3]
    return code[:2]


def normalise(rec, famille):
    adresses = deplie(rec.get("adresse"))
    postale = next((a for a in adresses if a.get("type_adresse") == "Adresse"),
                   adresses[0] if adresses else {})
    voie = ", ".join(x for x in (postale.get("complement1"), postale.get("complement2"),
                                 postale.get("numero_voie")) if x)
    ville = " ".join(x for x in (postale.get("code_postal"), postale.get("nom_commune")) if x)
    tels = deplie(rec.get("telephone"))
    sites = deplie(rec.get("site_internet"))
    return {
        "type": famille,
        "nom": (rec.get("nom") or "").strip(),
        "siren": rec.get("siren") or "",
        "dept": departement(rec.get("code_insee_commune")),
        "adresse": ", ".join(x for x in (voie, ville) if x),
        "tel": (tels[0].get("valeur", "") if tels else ""),
        "email": rec.get("adresse_courriel") or "",
        "contact": rec.get("formulaire_contact") or (sites[0].get("valeur", "") if sites else ""),
        "web": (sites[0].get("valeur", "") if sites else ""),
    }


def main():
    sortie = pathlib.Path(sys.argv[1])
    tout = []
    for famille, clause in FAMILLES:
        page, gardes = 0, 0
        while True:
            url = (f"{BASE}?where={urllib.parse.quote(clause)}"
                   f"&limit=100&offset={page * 100}&select={CHAMPS}")
            data = recupere(url)
            if data is None:
                print(f"  ⚠ {famille} : page {page + 1} injoignable, famille interrompue",
                      flush=True)
                break
            lots = data.get("results", [])
            for rec in lots:
                o = normalise(rec, famille)
                if o["dept"] in PACA and o["nom"]:
                    tout.append(o)
                    gardes += 1
            if len(lots) < 100 or page * 100 > (data.get("total_count") or 0):
                break
            page += 1
            time.sleep(0.3)
        print(f"  {famille:<12} {gardes:>3} en PACA", flush=True)

    # Dédoublonnage : l'annuaire publie parfois plusieurs fiches par organisme
    unique = {}
    for o in tout:
        cle = o["siren"] or (o["nom"], o["dept"])
        garde = unique.get(cle)
        # à doublon, on garde la fiche la mieux renseignée
        if not garde or (bool(o["email"]), bool(o["tel"])) > (bool(garde["email"]), bool(garde["tel"])):
            unique[cle] = o
    resultat = sorted(unique.values(), key=lambda o: (o["type"], o["dept"], o["nom"]))

    sortie.write_text(json.dumps(resultat, ensure_ascii=False, indent=1), encoding="utf-8")
    avec_mail = sum(1 for o in resultat if o["email"])
    print(f"\n{len(resultat)} organismes retenus après dédoublonnage, "
          f"{avec_mail} avec une adresse e-mail")


if __name__ == "__main__":
    main()
