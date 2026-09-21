#!/usr/bin/env python3
"""Cherche l'adresse de contact de chaque Epl sur son propre site.

L'export de l'annuaire des Epl ne porte aucune colonne e-mail : la seule piste
ouverte est le site de chaque structure. Le script visite l'accueil puis
quelques pages de contact usuelles, et retient l'adresse la plus plausible.

Écarte : les adresses d'agences web et de prestataires (souvent en pied de
page), les images, et les domaines sans rapport avec celui du site — une
adresse trouvée sur un site n'est retenue que si son domaine est celui du site
ou un domaine manifestement lié.

Usage : python3 annuaires/collecte_mails_epl.py SORTIE.json
"""
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent.parent
PAGE = RACINE / "annuaire-sem-spl-syndicats.html"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}

CHEMINS = ["", "/contact", "/contact.html", "/nous-contacter", "/contactez-nous",
           "/mentions-legales", "/mentions-legales.html"]

RE_MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Prestataires, plateformes et faux positifs courants en pied de page
REJET = re.compile(r"(wix|squarespace|wordpress|sentry|example|domain|your|sentry\.io|"
                   r"godaddy|ovh\.net|gandi|1and1|ionos|webmaster@|no-?reply|"
                   r"\.(png|jpe?g|gif|webp|svg|css|js)$)", re.I)
PREFERES = ("contact", "accueil", "info", "secretariat", "direction", "siege")


def texte(url, delai=12):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=delai) as r:
            brut = r.read(600_000)
        return brut.decode("utf-8", errors="replace")
    except Exception:
        return ""


def domaine(url):
    return re.sub(r"^www\.", "", re.sub(r"^https?://", "", url).split("/")[0]).lower()


def candidates(html, dom):
    trouvees = []
    for m in RE_MAIL.findall(html):
        m = m.strip(".,;:)»\"'")
        if REJET.search(m):
            continue
        d = m.split("@")[1].lower()
        # le domaine doit être celui du site, ou en partager la racine
        racine_site = dom.split(".")[0]
        if d == dom or d.endswith("." + dom) or racine_site[:6] in d:
            trouvees.append(m.lower())
    return trouvees


def meilleure(liste):
    if not liste:
        return ""
    for prefixe in PREFERES:
        for m in liste:
            if m.split("@")[0].startswith(prefixe):
                return m
    return liste[0]


def main():
    sortie = pathlib.Path(sys.argv[1])
    html = PAGE.read_text(encoding="utf-8")
    entrees = re.findall(r'^  \{nom:"([^"]*)".*?web:"([^"]*)".*?siren:"(\d{9,})"\}',
                         html, re.M)
    avec_site = [(nom, web, siren) for nom, web, siren in entrees if web]
    print(f"{len(entrees)} structures, {len(avec_site)} avec un site", flush=True)

    resultats, trouves = {}, 0
    for n, (nom, web, siren) in enumerate(avec_site, 1):
        base = "https://" + web.rstrip("/")
        dom = domaine(base)
        vues = []
        for chemin in CHEMINS:
            page = texte(base + chemin)
            if page:
                vues += candidates(page, dom)
                if any(m.split("@")[0].startswith(PREFERES) for m in vues):
                    break
            time.sleep(0.2)
        # dédoublonnage en conservant l'ordre de découverte
        vues = list(dict.fromkeys(vues))
        choix = meilleure(vues)
        if choix:
            trouves += 1
            resultats[siren] = choix
            print(f"  [{n:>3}/{len(avec_site)}] {nom[:46]:<48} {choix}", flush=True)
        else:
            print(f"  [{n:>3}/{len(avec_site)}] {nom[:46]:<48} —", flush=True)
        sortie.write_text(json.dumps(resultats, ensure_ascii=False, indent=1))

    print(f"\nTerminé : {trouves} adresses sur {len(avec_site)} sites visités "
          f"({len(entrees)} structures au total)", flush=True)


if __name__ == "__main__":
    main()
