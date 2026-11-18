#!/usr/bin/env python3
"""Rebalaye les sources officielles pour compléter e-mails et téléphones.

Produit `annuaires/contacts_complementaires.json`, que `build_prospection.py`
applique à chaque régénération : une adresse trouvée ici n'est jamais perdue
quand une famille est reprise de la page existante.

Sources, par ordre de confiance :
  1. BANATIC officiel (banatic.interieur.gouv.fr, export national) pour les
     syndicats : courriel, téléphone et site du siège. La copie OpenDataSoft
     utilisée jusque-là ne portait aucune de ces colonnes.
  2. Annuaire de l'éducation (data.education.gouv.fr) pour les associations
     gestionnaires d'établissements scolaires, rapprochées par SIREN.
  3. FINESS (data.gouv.fr) pour le téléphone des associations sanitaires et
     médico-sociales, rapprochées par SIREN. FINESS ne publie pas d'e-mail.
  4. Le site de l'organisme quand une source officielle le donne : accueil et
     pages de contact, avec les garde-fous de `collecte_mails_epl.py` (l'adresse
     doit porter le domaine du site).

  5. Avec `--cherche-sites`, pour les organismes dont aucune source ne donne le
     site : des noms de domaine plausibles (sigle, nom) sont essayés, et un site
     n'est retenu que s'il **affiche le SIREN de l'organisme** — en général dans
     ses mentions légales. Sans ce SIREN, le site est ignoré.

Aucune adresse n'est devinée ni construite : une entrée sans source reste vide.

Usage : python3 annuaires/enrichit_contacts.py CACHE [--sans-sites] [--cherche-sites]
  CACHE contient banatic_paca.json, education.json, finess.csv, associations.json
"""
import csv
import json
import pathlib
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collecte_mails_epl import CHEMINS, PREFERES, candidates, domaine, meilleure, texte

RACINE = pathlib.Path(__file__).resolve().parent.parent
SORTIE = pathlib.Path(__file__).resolve().parent / "contacts_complementaires.json"
EPL = RACINE / "annuaire-sem-spl-syndicats.html"
RE_MAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def norme(nom):
    """Clé de rapprochement par nom : sans accent, sans ponctuation, en capitales."""
    s = unicodedata.normalize("NFD", nom or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"[^A-Z0-9]+", " ", s).strip()


def cle_nom(nom, dept):
    return f"nom:{norme(nom)}|{dept}"


EXTENSIONS = ("fr", "com", "org", "net", "eu", "info", "pro", "gouv.fr", "asso.fr", "coop", "mc", "email")


def mail_valide(v):
    v = (v or "").strip().strip(";,").split(";")[0].split(",")[0].strip().lower()
    if not RE_MAIL.match(v):
        return ""
    # Sur une page, l'adresse est parfois collée au mot suivant (« …@site.frTél ») :
    # l'extension est ramenée à celle, connue, par laquelle elle commence.
    local, dom = v.rsplit("@", 1)
    if not dom.endswith(tuple("." + e for e in EXTENSIONS)):
        m = re.match(r"^(.*\.(?:fr|com|org|net|eu))[a-z]+$", dom)
        if not m:
            return ""
        dom = m.group(1)
    return f"{local}@{dom}"


def tel_propre(v):
    c = re.sub(r"\D", "", v or "")
    if len(c) == 9:
        c = "0" + c
    return " ".join(c[i:i + 2] for i in range(0, 10, 2)) if len(c) == 10 and c[0] == "0" else ""


def site_propre(v):
    v = (v or "").strip()
    if not v or " " in v or "." not in v:
        return ""
    return v if v.startswith("http") else "https://" + v


def fouille(site):
    """Meilleure adresse trouvée sur un site, ou chaîne vide."""
    base = site.rstrip("/")
    dom = domaine(base)
    vues = []
    for chemin in CHEMINS:
        page = texte(base + chemin, delai=10)
        if page:
            vues += candidates(page, dom)
            if any(m.split("@")[0].startswith(PREFERES) for m in vues):
                break
    return meilleure(list(dict.fromkeys(vues)))


VIDES = {"ASS", "ASSO", "ASSOC", "ASSOCIATION", "ASSOCIATIONS", "DE", "DU", "DES", "LA", "LE",
         "LES", "L", "D", "ET", "POUR", "EN", "AU", "AUX", "A", "SUR", "SM", "SYNDICAT", "MIXTE",
         "INTERCOMMUNAL", "SIVU", "SIVOM", "SOCIETE", "SA", "SEM", "SPL"}
PAGES_LEGALES = ["", "/mentions-legales", "/mentions-legales/", "/mentions-legales.html",
                 "/mentions", "/contact"]


def domaines_plausibles(nom, sigle=""):
    mots = [m.lower() for m in norme(nom).split() if m not in VIDES and len(m) > 1]
    bases = []
    if sigle and len(norme(sigle).replace(" ", "")) >= 3:
        bases.append(norme(sigle).replace(" ", "").lower())
        bases.append(norme(sigle).replace(" ", "-").lower())
    if mots:
        bases += ["".join(mots), "-".join(mots), "".join(mots[:2]), "-".join(mots[:2]),
                  "".join(mots[:3]), "-".join(mots[:3])]
    bases = [b for b in dict.fromkeys(bases) if 4 <= len(b) <= 40]
    return [f"https://www.{b}{tld}" for b in bases[:5] for tld in (".fr", ".org", ".asso.fr", ".com")]


def cherche_site(args):
    """Premier domaine plausible dont une page affiche le SIREN ; (site, mail)."""
    siren, nom, sigle = args
    motif = re.compile(r"(?<!\d)" + r"[\s\u00a0.]?".join(
        (siren[:3], siren[3:6], siren[6:])) + r"(?!\d{6,})")
    for base in domaines_plausibles(nom, sigle):
        accueil = texte(base, delai=6)
        if not accueil:
            continue
        pages = [accueil] + [texte(base + c, delai=6) for c in PAGES_LEGALES[1:]]
        if not any(motif.search(p) for p in pages if p):
            continue
        vues = []
        for p in pages:
            vues += candidates(p, domaine(base)) if p else []
        return base, meilleure(list(dict.fromkeys(vues)))
    return "", ""


def main():
    cache = pathlib.Path(sys.argv[1])
    sans_sites = "--sans-sites" in sys.argv
    contacts, a_fouiller = {}, {}

    def poser(cle, source, email="", tel="", web=""):
        c = contacts.setdefault(cle, {"email": "", "tel": "", "web": "", "source": ""})
        ajout = False
        for champ, valeur in (("email", email), ("tel", tel), ("web", web)):
            if valeur and not c[champ]:
                c[champ] = valeur
                ajout = True
        if ajout and source not in c["source"]:
            c["source"] = (c["source"] + " + " + source).strip(" +")

    # 1. Syndicats — BANATIC officiel
    for g in json.loads((cache / "banatic_paca.json").read_text(encoding="utf-8")):
        cle = cle_nom(g["nom"], g["dept"])
        poser(cle, "BANATIC", mail_valide(g["email"]), tel_propre(g["tel"]), site_propre(g["web"]))
        if site_propre(g["web"]) and not mail_valide(g["email"]):
            a_fouiller[cle] = site_propre(g["web"])

    # 2 et 3. Associations — annuaire de l'éducation puis FINESS, par SIREN
    assos = json.loads((cache / "associations.json").read_text(encoding="utf-8"))
    sirens = {a["siren"]: a for a in assos}
    ecoles = {}
    for e in json.loads((cache / "education.json").read_text(encoding="utf-8")):
        siren = (e.get("siren_siret") or "")[:9]
        if siren in sirens and e.get("statut_public_prive") != "Public":
            ecoles.setdefault(siren, []).append(e)
    for siren, liste in ecoles.items():
        liste.sort(key=lambda e: (not e.get("mail"), e.get("siren_siret") or ""))
        e = liste[0]
        poser(f"siren:{siren}", "Annuaire de l'éducation", mail_valide(e.get("mail")),
              tel_propre(e.get("telephone")), site_propre(e.get("web")))
        if site_propre(e.get("web")) and not mail_valide(e.get("mail")):
            a_fouiller[f"siren:{siren}"] = site_propre(e.get("web"))

    etabs = {}
    with open(cache / "finess.csv", encoding="latin-1", newline="") as f:
        for l in csv.reader(f, delimiter=";"):
            if len(l) > 22 and l[0] == "structureet" and l[22][:9] in sirens:
                etabs.setdefault(l[22][:9], []).append((l[15][:5], tel_propre(l[16])))
    for siren, liste in etabs.items():
        numeros = {t for _, t in liste if t}
        cp_siege = (re.findall(r"\b(\d{5})\b", sirens[siren]["adresse"]) or [""])[-1]
        au_siege = {t for cp, t in liste if t and cp == cp_siege}
        # Le numéro d'un établissement n'est retenu que s'il est le seul connu
        # ou s'il est au code postal du siège : sinon on appellerait un foyer.
        choix = numeros if len(numeros) == 1 else au_siege if len(au_siege) == 1 else set()
        if choix:
            poser(f"siren:{siren}", "FINESS", tel=choix.pop())

    # 4. Epl sans adresse mais avec un site
    html = EPL.read_text(encoding="utf-8")
    for ligne in re.findall(r"^  \{nom:.*\}", html, re.M):
        e = dict(re.findall(r'(\w+):"([^"]*)"', ligne))
        if e.get("web") and not e.get("email"):
            a_fouiller[cle_nom(e["nom"], e.get("depcode", ""))] = site_propre(e["web"])

    officiels = sum(1 for c in contacts.values() if c["email"])
    if not sans_sites and a_fouiller:
        print(f"{len(a_fouiller)} sites à visiter…", flush=True)
        with ThreadPoolExecutor(max_workers=12) as pool:
            for cle, mail in zip(a_fouiller, pool.map(fouille, a_fouiller.values())):
                if mail_valide(mail):
                    poser(cle, "site de l'organisme", email=mail_valide(mail))

    if "--cherche-sites" in sys.argv:
        cibles = {}
        for a in assos:
            if not contacts.get(f"siren:{a['siren']}", {}).get("email"):
                cibles[f"siren:{a['siren']}"] = (a["siren"], a["nom"], a.get("sigle", ""))
        for g in json.loads((cache / "banatic_paca.json").read_text(encoding="utf-8")):
            cle = cle_nom(g["nom"], g["dept"])
            if g["nature"] in ("SIVU", "SIVOM", "SMF", "SMO", "PETR", "POLEM") \
                    and not contacts.get(cle, {}).get("email") and not site_propre(g["web"]):
                sigle = (re.findall(r"\(([A-Z0-9 ]{3,12})\)", g["nom"]) or [""])[0]
                cibles[cle] = (g["siren"], re.sub(r"\(.*?\)", "", g["nom"]), sigle)
        print(f"{len(cibles)} organismes sans site connu : recherche vérifiée par SIREN…", flush=True)
        trouves = 0
        with ThreadPoolExecutor(max_workers=32) as pool:
            for cle, (site, mail) in zip(cibles, pool.map(cherche_site, cibles.values())):
                if site:
                    trouves += 1
                    poser(cle, "site de l'organisme (SIREN vérifié)", email=mail_valide(mail), web=site)
        print(f"   {trouves} sites confirmés par leur SIREN", flush=True)

    contacts = {k: v for k, v in sorted(contacts.items()) if v["email"] or v["tel"] or v["web"]}
    SORTIE.write_text(json.dumps(contacts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    mails = sum(1 for c in contacts.values() if c["email"])
    print(f"✅ {SORTIE.name} — {len(contacts)} organismes complétés : {mails} e-mails "
          f"({officiels} de source officielle, {mails - officiels} relevés sur les sites), "
          f"{sum(1 for c in contacts.values() if c['tel'])} téléphones")


if __name__ == "__main__":
    main()
