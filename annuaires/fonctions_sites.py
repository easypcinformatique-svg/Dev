#!/usr/bin/env python3
"""Relève sur le site de chaque organisme les dirigeants qu'il publie lui-même.

Lit l'accueil, les pages de gouvernance, d'équipe, d'organigramme et les
mentions légales, et y cherche un nom accolé à une fonction : président,
directeur général, directeur, directeur ou responsable financier, et à défaut
le directeur de la publication, que les mentions légales doivent nommer.

C'est la seule source pour les associations, qui ne déclarent leurs dirigeants
dans aucun registre ouvert, et pour les directeurs financiers. Un nom relevé
ainsi date de la dernière mise à jour du site : à vérifier avant usage.

Usage : python3 annuaires/fonctions_sites.py CACHE   -> CACHE/fonctions_sites.json
"""
import html
import json
import pathlib
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fouille_profonde as F

RE_PAGES = re.compile(r"organigramme|gouvernance|equipe|[ée]quipe|direction|qui-sommes|organisation|"
                      r"conseil-d-administration|administrateurs|bureau|comite|presentation|"
                      r"a-propos|association|mentions|l[eé]gal|instances|elus|[ée]lus", re.I)
P = r"(?:[A-ZÉÈ][a-zéèêëïîôçñ]+(?:-[A-ZÉÈ][a-zéèêëïîôçñ]+)?)"
N = r"(?:[A-ZÉÈ][A-ZÉÈa-zéèêëïîôçñ'\-]+(?:\s+[A-ZÉÈ]{2,}[A-ZÉÈ'\-]*)?)"
NOM = rf"((?:{P}\s+{N})|(?:[A-ZÉÈ]{{2,}}[A-ZÉÈ'\-]*\s+{P}))"
CIV = r"(?:(?:M\.|Mme|Mr|Madame|Monsieur|Dr|Docteur|Me|Maître)\s+)?"
SEP = r"\s*(?:[·,:\-–—|]\s*){0,4}"
FIN = (r"(?:[Aa]dministrati(?:f|ve)\s+et\s+[Ff]inanci(?:er|[èe]re)|[Ff]inanci(?:er|[èe]re)|"
       r"(?:des\s+)?[Ff]inances|des\s+[Aa]ffaires\s+[Ff]inanci[èe]res|[Aa]dministration\s+et\s+[Ff]inances)")
ROLES = [
    ("DAF", rf"(?:Direct(?:eur|rice)|Responsable)\s+(?:[Gg][ée]n[ée]rale?\s+[Aa]djointe?\s+)?{FIN}|\bDAF\b|\bRAF\b"),
    ("Président", r"Pr[ée]sidente?(?!\s+(?:d'honneur|honoraire|de\s+la\s+commission|de\s+s[ée]ance|du\s+comit[ée]|de\s+la\s+R[ée]publique|du\s+Conseil\s+d[ée]partemental|de\s+la\s+R[ée]gion|adjoint))(?:\s+du\s+(?:[Cc]onseil\s+d'[Aa]dministration|[Dd]irectoire))?"),
    ("DG", r"Direct(?:eur|rice)\s+[Gg][ée]n[ée]rale?(?!\s+[Aa]djoint)(?:\s+des\s+[Ss]ervices)?|\bDGS\b"),
    ("Directeur", r"Direct(?:eur|rice)(?:\s+de\s+l'(?:association|[ée]tablissement))?(?!\s+(?:de\s+la\s+publication|de\s+publication|g[ée]n[ée]ral|adjoint|financ|administrati|des|du|de|d'|technique|commercial|artistique|m[ée]dical|p[ée]dagogique|\w+))"),
    ("Dir. publication", r"(?:Direct(?:eur|rice)|Responsable)\s+(?:de\s+la\s+|de\s+)publication"),
]
STOP = set("""Le La Les Un Une Des Du De Notre Nos Votre Vos Direction Directeur Directrice Service Services
Pôle Pole Responsable Madame Monsieur Président Présidente Conseil Comité Groupe Finances Financier
Financière Général Générale Adjoint Adjointe Ressources Humaines Patrimoine Communication Contact
Accueil Secrétaire Siège Gestion Administration Administratif Développement Habitat Logement Marchés
Juridique Mission Missions Chargé Chargée Chef Maîtrise Proximité Clientèle Territoire Territoires
Agence Qualité Systèmes Information Stratégie Depuis Diplômé Ancien Ancienne Nommé Nommée Poste
Emploi Offre Recrutement Profil Nous Vous Il Elle Membre Membres Voir Plus En Sous Pour Avec Sur Dans
Et Ou Au Aux Organigramme Équipe Equipe Publié Mis Télécharger Découvrir Lire Suite Mentions Légales
Hébergeur Hébergement Editeur Éditeur Site Internet Web Publication Rédaction Adresse Téléphone Tél
Email Courriel Mail Association Société Fondation Mairie Ville Commune Communauté Agglomération
Métropole Département Région Provence Alpes Côte Azur Sud France Marseille Nice Toulon Avignon Aix
Bureau Trésorier Trésorière Vice Délégué Déléguée Mot Édito Edito Bienvenue Cliquez Ici Tous Toutes
Rapport Annuel Activité Actualités Agenda Projet Projets Politique Confidentialité Cookies Crédits
Conception Réalisation Design Agence Studio Copyright Droits Réservés Propriété Intellectuelle
Représentant Représentée Représenté Légal Légale Qualité Cette Cet Ce Son Sa Ses Leur Assemblée
Générale Statutaire Composition Honneur Santé Social Sociale Médico Enfance Jeunesse Handicap""".split())


def nom_ok(n):
    t = n.split()
    return 2 <= len(t) <= 3 and len(n) <= 40 and not any(x in STOP or x.title() in STOP for x in t) \
        and not any(len(x) < 2 for x in t)


def texte(p):
    p = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", p)
    p = html.unescape(re.sub(r"<[^>]+>", " · ", p))
    return re.sub(r"\s+", " ", p)


def lire_site(site):
    final, accueil = F.lire(site)
    if not accueil:
        return ""
    h, pages, vus, a_voir = F.hote(final), [accueil], set(), []
    for href, libelle in F.RE_LIEN.findall(accueil):
        if RE_PAGES.search(href) or RE_PAGES.search(re.sub(r"<[^>]+>", " ", libelle)):
            u = urllib.parse.urljoin(final, href.strip())
            if u.startswith("http") and F.hote(u) == h and u not in vus \
                    and not re.search(r"\.(pdf|jpe?g|png|docx?)(\?|$)", u, re.I):
                vus.add(u)
                a_voir.append(u)
    a_voir.sort(key=lambda u: (not re.search(r"gouvernance|organigramme|equipe|mention|l[eé]gal", u, re.I), len(u)))
    for u in a_voir[:7]:
        _, p = F.lire(u)
        if p:
            pages.append(p)
    return " ".join(texte(p) for p in pages)


def fonctions(site):
    t = lire_site(site)
    trouve = {}
    for role, motif in ROLES:
        for rx in (rf"(?:{motif}){SEP}{CIV}{NOM}", rf"{CIV}{NOM}{SEP}(?:{motif})(?![a-zéè])"):
            for m in re.finditer(rx, t):
                n = re.sub(r"\s+", " ", m.group(1)).strip()
                if nom_ok(n):
                    trouve[role] = n
                    break
            if role in trouve:
                break
    # Le directeur de la publication n'apprend rien s'il porte déjà une autre fonction.
    if trouve.get("Dir. publication") in [v for k, v in trouve.items() if k != "Dir. publication"]:
        del trouve["Dir. publication"]
    return trouve


def main():
    cache = pathlib.Path(sys.argv[1])
    bloc = re.search(r"const DATA = \[\n([\s\S]*?)\n\];", F.PAGE.read_text(encoding="utf-8")).group(1)
    entrees = [dict(re.findall(r'(\w+):"([^"]*)"', l)) for l in bloc.splitlines()]
    contacts = json.loads(F.SORTIE.read_text(encoding="utf-8"))
    assos = json.loads((cache / "associations.json").read_text(encoding="utf-8"))
    par_nom = {(a["nom"] + (f' ({a["sigle"]})' if a.get("sigle") else ""), a["dept"]): a["siren"]
               for a in assos}
    cibles = {}
    for e in entrees:
        if not e.get("type"):
            continue
        if e["type"].startswith("Association"):
            cle = "siren:" + par_nom.get((e["nom"], e["dept"]), "")
        else:
            cle = F.cle_nom(e["nom"], e["dept"])
        site = F.site_net(contacts.get(cle, {}).get("web", "")) or F.site_net(e.get("contact", ""))
        if not site and e.get("email") and e["email"].split("@")[1] not in F.MESSAGERIES:
            site = "https://" + e["email"].split("@")[1]
        if site:
            cibles[cle] = site
    print(f"{len(cibles)} sites à lire", flush=True)
    resultat = {}
    with ThreadPoolExecutor(max_workers=40) as pool:
        for cle, f in zip(cibles, pool.map(fonctions, cibles.values())):
            if f:
                resultat[cle] = f
    (cache / "fonctions_sites.json").write_text(json.dumps(resultat, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    from collections import Counter
    print(f"✅ {len(resultat)} organismes avec au moins un nom publié",
          dict(Counter(r for f in resultat.values() for r in f)))


if __name__ == "__main__":
    main()
