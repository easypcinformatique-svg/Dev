#!/usr/bin/env python3
"""Injecte dans la page des Epl les adresses collectées sur leurs sites.

Ne remplit que les entrées dont le champ email est vide : une adresse déjà
présente vient du workflow hebdomadaire, qui l'a confirmée sur la fiche
publique de l'entreprise, et ne doit pas être écrasée.

Le remplacement se fait entrée par entrée, comme le fait update-sem-spl-sm.yml,
pour ne pas reformater le tableau ni perdre les clés qu'il ne connaît pas.

Usage : python3 annuaires/applique_mails_epl.py ADRESSES.json
"""
import json
import pathlib
import re
import sys

PAGE = pathlib.Path(__file__).resolve().parent.parent / "annuaire-sem-spl-syndicats.html"
RE_MAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# Même contrainte qu'à la génération : les regex de relecture capturent avec
# [^"]*, donc ni guillemet double ni antislash dans une valeur.
INTERDIT = re.compile(r'["\\]')


def main():
    adresses = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    html = PAGE.read_text(encoding="utf-8")

    motif = re.compile(r'\{nom:"([^"]*)".*?email:"([^"]*)".*?siren:"(\d{9,})"\}')
    remplacements, ignorees, deja = [], [], 0

    for m in motif.finditer(html):
        nom, email_actuel, siren = m.groups()
        candidate = (adresses.get(siren) or "").strip().lower()
        if not candidate:
            continue
        if email_actuel:
            deja += 1
            continue
        if not RE_MAIL.match(candidate) or INTERDIT.search(candidate):
            ignorees.append((nom, candidate))
            continue
        entree = html[m.start():m.end()]
        remplacements.append((m.start(), m.end(),
                              entree.replace('email:""', f'email:"{candidate}"')))

    for debut, fin, texte in sorted(remplacements, reverse=True):
        html = html[:debut] + texte + html[fin:]
    PAGE.write_text(html, encoding="utf-8")

    total = len(motif.findall(html))
    avec = len(re.findall(r'email:"[^"]+"', html))
    print(f"✅ {len(remplacements)} adresses injectées "
          f"({avec} sur {total} structures en ont une désormais)")
    if deja:
        print(f"   {deja} déjà renseignées, laissées en l'état")
    for nom, valeur in ignorees:
        print(f"   ⚠ écartée — {nom[:44]} : {valeur}")


if __name__ == "__main__":
    main()
