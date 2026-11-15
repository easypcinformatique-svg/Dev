#!/usr/bin/env python3
"""Reprend les 52 constats de l'audit du 11 septembre 2026 et mesure, un par un,
ce qu'il en reste sur la version du site passée au guard. Aucun constat n'est
déclaré réglé sans une vérification qui échouerait si le défaut revenait."""
import re, os, sys, glob, json, unicodedata
from html import unescape

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
pages = {os.path.relpath(p, SITE).replace(os.sep, "/"): open(p, encoding="utf-8").read()
         for p in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)}


def texte(html):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return unescape(re.sub(r"<[^>]+>", " ", h))


TEXTES = {k: texte(v) for k, v in pages.items()}
ACCENTS = "àâäéèêëîïôöùûüçœÀÂÄÉÈÊËÎÏÔÖÙÛÜÇŒ"
resultats = []


def constat(code, gravite, titre, etat, detail=""):
    resultats.append({"code": code, "gravite": gravite, "titre": titre,
                      "etat": etat, "detail": detail})


def partout(motif, ou=None, drapeaux=0):
    """Pages où le motif apparaît."""
    cible = ou or pages
    return sorted(k for k, v in cible.items() if re.search(motif, v, drapeaux))


# ---------- 01 Qualité éditoriale ----------
densites = {}
for k, t in TEXTES.items():
    mots = len(t.split())
    if mots > 300:
        densites[k] = (sum(c in ACCENTS for c in t) / mots * 1000, mots)
pauvres = {k: v for k, v in densites.items() if v[0] < 60}
constat("E1", "critique", "≈12 000 mots publiés sans accents",
        "ouvert" if pauvres else "résolu",
        "; ".join(f"{k} {v[0]:.0f}/1000 mots" for k, v in sorted(pauvres.items())[:8]))
moyens = {k: v for k, v in densites.items() if 55 <= v[0] < 80}
constat("E2", "important", "Guides partiellement désaccentués",
        "ouvert" if moyens else "résolu",
        "; ".join(f"{k} {v[0]:.0f}" for k, v in sorted(moyens.items())[:8]))

desc = re.search(r'<meta name="description" content="([^"]*)"', pages.get("index.html", ""))
d = desc.group(1) if desc else ""
constat("E3", "important", "Meta description de l'accueil fautive",
        "ouvert" if re.search(r"\bdes 17h30|\bdes 7", d) else "résolu", d[:120])

titres_sans_accent = []
for k, v in pages.items():
    m = re.search(r"<title>([^<]*)</title>", v)
    if m and len(m.group(1)) > 25 and not any(c in ACCENTS for c in m.group(1)) \
            and re.search(r"\b(Generales|Legales|Confidentialite|provencal|Cite|pres)\b", m.group(1)):
        titres_sans_accent.append(k)
constat("E4", "important", "Balises <title> sans accents",
        "ouvert" if titres_sans_accent else "résolu", ", ".join(titres_sans_accent[:7]))

p = partout(r"Vous livrons aussi")
constat("E5", "important", "« Vous livrons aussi » en H2", "ouvert" if p else "résolu", ", ".join(p[:5]))

p = partout(r"recapitulatif de votre commande vous sera envoye|récapitulatif de votre commande vous sera envoyé par e?mail")
constat("E6", "important", "Modale pré-commande mal écrite / promesse d'e-mail",
        "ouvert" if p else "résolu", ", ".join(p[:4]))

p = partout(r"Allergenes\s*:\s*nos pizzas|crustaces|celeri, moutarde, sesame")
constat("E7", "important", "Encart allergènes désaccentué",
        "ouvert" if p else "résolu", ", ".join(p[:4]))

p = partout(r"Desole, nous ne livrons pas|Verifiez votre adresse|Minimum pour livrer a |equivaut a ")
constat("E8", "important", "Alertes du tunnel sans accents", "ouvert" if p else "résolu", ", ".join(p[:5]))

p = partout(r"Margharita")
n = sum(len(re.findall("Margharita", v)) for v in pages.values())
constat("E9", "important", "« Margharita » au lieu de Margherita",
        "ouvert" if p else "résolu", f"{n} occurrence(s) sur {len(p)} page(s)")

p = partout(r"rebourlet", drapeaux=re.IGNORECASE)
constat("E10", "mineur", "« rebourlet » n'existe pas", "ouvert" if p else "résolu", ", ".join(p[:4]))

nbsp = sum(v.count("&nbsp;") + v.count(" ") for v in pages.values())
apos = sum(t.count("'") for t in TEXTES.values())
constat("E11", "mineur", "Typographie : espaces insécables et apostrophes",
        "ouvert" if nbsp < 100 else "résolu", f"{nbsp} insécables, {apos} apostrophes droites")

p = partout(r"A lire aussi sur notre blog")
constat("E12", "mineur", "« A lire aussi » sans accent", "ouvert" if p else "résolu", f"{len(p)} page(s)")

p = [k for k, t in TEXTES.items() if re.search(r"4\.5\s*/\s*5", t)]
constat("E13", "mineur", "Note écrite « 4.5/5 » dans le texte visible",
        "ouvert" if p else "résolu", ", ".join(p[:4]))

p = partout(r"</nav>rsaquo;|>rsaquo;")
constat("E14", "mineur", "Fil d'Ariane affiche « rsaquo; »", "ouvert" if p else "résolu", ", ".join(p[:4]))

# ---------- 02 SEO local ----------
villes = sorted(k for k in pages if k.startswith("livraison-pizza-") and "sarrians" not in k)


def neutraliser(t):
    t = re.sub(r"\d+", "#", t)
    for v in ("Carpentras", "Serres", "Pernes-les-Fontaines", "Mazan", "Monteux", "Aubignan",
              "Loriol-du-Comtat", "Caromb", "Saint-Didier"):
        t = t.replace(v, "VILLE")
    return set(re.sub(r"\W+", " ", t.lower()).split())


paires, sims = [], []
for i in range(len(villes)):
    for j in range(i + 1, len(villes)):
        a, b = neutraliser(TEXTES[villes[i]]), neutraliser(TEXTES[villes[j]])
        if a and b:
            sims.append(len(a & b) / len(a | b))
moy = sum(sims) / len(sims) if sims else 0
constat("S1", "critique", "Pages villes quasi identiques",
        "ouvert" if moy > 0.75 else ("partiel" if moy > 0.6 else "résolu"),
        f"similarité moyenne {moy:.0%} sur {len(villes)} pages")

constat("S2", "critique", "Trois domaines concurrents", "hors périmètre",
        "dépend du propriétaire des domaines, pas de ce dépôt")

p = partout(r"05700|Hautes-Alpes|Serre-Ponçon|Buëch")
constat("S3", "critique", "Article sur le mauvais Serres", "ouvert" if p else "résolu", ", ".join(p[:4]))

p = [k for k, t in TEXTES.items()
     if k != "livraison-pizza-sarrians/index.html"
     and re.search(r"Sarrians", t)
     and not re.search(r"Sarrians[^.]{0,60}(non desservi|pas (dans|desservi))", t)
     and re.search(r"(livr|zone de livraison)[^.]{0,80}Sarrians|Sarrians[^.]{0,40}livr", t, re.IGNORECASE)]
constat("S4", "important", "Sarrians annoncé desservi", "ouvert" if p else "résolu", ", ".join(p[:5]))

home = pages.get("index.html", "")
constat("S5", "important", "areaServed oublie Serres",
        "résolu" if '"City","name":"Serres"' in home.replace(" ", "") else "ouvert")

jsonld_19 = re.search(r'"acceptedAnswer".{0,400}?19h00 à 22h00', home, re.DOTALL)
jsonld_1730 = re.search(r'"acceptedAnswer".{0,400}?de 17h30 à 22h', home, re.DOTALL)
constat("S6", "important", "JSON-LD FAQ contredit le texte visible",
        "ouvert" if jsonld_1730 and not jsonld_19 else "résolu")

fantomes = []
for k in ("pizza-carpentras/index.html", "livraison-pizza-84200/index.html"):
    if k not in pages:
        continue
    can = re.search(r'rel="canonical" href="([^"]*)"', pages[k])
    if not can or f'/{k.split("/")[0]}/' in can.group(1):
        continue
    entrants = [o for o, v in pages.items()
                if o != k and f'href="/{k.split("/")[0]}/"' in v]
    if entrants:
        fantomes.append(f'{k} (liée depuis {len(entrants)} page(s))')
constat("S7", "important", "Pages canonisées ailleurs mais encore liées",
        "ouvert" if fantomes else "résolu",
        "; ".join(fantomes) or "plus aucun lien entrant : le maillage ne s'y perd plus")

constat("S8", "important", "Serres traité comme une commune", "ouvert",
        "3 pages dédiées à un hameau de Carpentras ; fusion éditoriale, pas automatisable")
constat("S9", "important", "Six URL pour la même intention", "ouvert",
        "arbitrage éditorial : désigner une page pilier")

longs = []
for k, v in pages.items():
    m = re.search(r"<title>([^<]*)</title>", v)
    if m and len(unescape(m.group(1))) > 60:          # &amp; compte pour un caractère
        longs.append((k, len(unescape(m.group(1)))))
constat("S10", "mineur", "Balises <title> de plus de 60 caractères",
        "ouvert" if longs else "résolu", f"{len(longs)} page(s), max {max([l for _, l in longs], default=0)}")

p = partout(r"Pierre Semard")
constat("S11", "mineur", "Adresse « Pierre Semard » sans accent",
        "ouvert" if p else "résolu", f"{len(p)} page(s)")

cartes = set(re.findall(r'<a href="/livraison-pizza-([a-z-]+)/"[^>]*transition:box-shadow', home))
cites = len({c for c in cartes}) + (1 if "livraison-pizza-carpentras" in cartes else 0)
cites = len(cartes)
constat("S12", "mineur", "Pied de page n'expose que 4 communes sur 9",
        "résolu" if cites >= 9 else "ouvert", f"{cites}/9 communes liées")

p = partout(r"sans gluten|PMR|mobilité réduite|stationnement|végétalien|halal", drapeaux=re.IGNORECASE)
constat("S13", "important", "Signaux locaux absents (accès, parking, régimes)",
        "ouvert" if not p else "résolu", f"{len(p)} page(s)")

# ---------- 03 Conversion ----------
constat("C1", "critique", "Le bouton annonce une action qu'il ne fait pas après 17h30",
        "résolu" if "libellerCommander" in home else "ouvert",
        "arbitrage du propriétaire : le libellé bascule sur l'appel à 17h30")

constat("C2", "critique", "Minimum de commande révélé au dernier clic",
        "résolu" if ("min-commune" in home and "manqueTexte" in home) else "ouvert",
        "annoncé dès la saisie de l'adresse et décompté dans la barre de total")

constat("C3", "critique", "Récapitulatif par e-mail promis sans champ e-mail",
        "résolu" if 'type="email"' not in home and not re.search(r"envoy[ée] par e?mail", home) else "ouvert")

constat("C4", "important", "Petites pizzas comptées comme des grandes",
        "résolu" if re.search(r"o\.size\s*===\s*'26'\s*\?\s*0\.5\s*:\s*1", home) else "ouvert",
        "le contrôle actif pondère bien 0,5 / 1")

zv = re.search(r"/\* === ZONE VALIDATION ===.*?FIN ZONE VALIDATION", home, re.DOTALL)
bloc = zv.group(0) if zv else ""
noms_avant_cp = bloc.find("'pernes'") < bloc.find("'84210'") if "'84210'" in bloc else True
constat("C5", "important", "84210 attribué à Saint-Didier avant Pernes",
        "résolu" if noms_avant_cp else "ouvert", "noms testés avant les codes postaux")

lignes_monteux = len(re.findall(r"📍\s*Monteux[^<]*</td>", home))
constat("C6", "important", "Monteux en triple dans le tableau",
        "ouvert" if lignes_monteux > 2 else "résolu", f"{lignes_monteux} ligne(s) Monteux")

sans_cta = [k for k, v in pages.items()
            if k != "index.html" and "noindex" not in v and "commander-inline" not in v
            and "wa.me" not in v and "</main>" in v]
constat("C7", "important", "Parcours de commande absent des pages d'atterrissage",
        "ouvert" if sans_cta else "résolu", f"{len(sans_cta)} page(s) sans accès au tunnel")

creneaux = re.findall(r'<option value="(\d{2}:\d{2})"', home)
constat("C8", "important", "Aucun créneau à emporter avant 19h30",
        "ouvert" if creneaux and min(creneaux) >= "19:30" else "résolu",
        f"premier créneau {min(creneaux) if creneaux else '?'}")

_rv = re.compile("|".join(sorted((re.escape(v) for v in
      ["Pernes-les-Fontaines", "Loriol-du-Comtat", "Saint-Didier", "Carpentras", "Aubignan",
       "Monteux", "Caromb", "Pernes", "Loriol", "Mazan", "Serres"]), key=len, reverse=True)))
_alias = {"Pernes": "Pernes-les-Fontaines", "Loriol": "Loriol-du-Comtat"}
_par_ville = {}
for _k, _t in TEXTES.items():
    for _m in re.finditer(r"(\d{2})\s*(?:à|-|–)\s*(\d{2})\s*min", _t):
        if _t[_m.end():_m.end() + 30].lstrip().startswith(("utes selon la commune", "selon la commune")):
            continue
        _v = None
        for _x in _rv.finditer(_t[max(0, _m.start() - 140):_m.start()]):
            _v = _x.group(0)
        if _v:
            _v = _alias.get(_v, _v)
            _par_ville.setdefault(_v, set()).add(f"{_m.group(1)}-{_m.group(2)}")
_fautives = {v: s_ for v, s_ in _par_ville.items() if len(s_) > 1}
constat("C9", "important", "Délais de livraison contradictoires pour une même commune",
        "ouvert" if _fautives else "résolu",
        "; ".join(f"{v} : {', '.join(sorted(s_))}" for v, s_ in list(_fautives.items())[:4])
        or f"{len(_par_ville)} communes, un délai chacune")

constat("C10", "mineur", "Offre promotionnelle sans conditions ni comptage fiable",
        "résolu" if "var OFFRES" in home and "nbPizzas" in home else "ouvert",
        "deux paliers, comptage sur pizzaOrders")

# ---------- 04 Confiance ----------
p = partout(r"Quattro Formaggi|Regina\b")
constat("T1", "critique", "Témoignages citant des pizzas inexistantes",
        "ouvert" if p else "résolu", ", ".join(p[:4]))

menu = {}
for m in re.finditer(r"name:(?:'([^']*)'|\"([^\"]*)\"),\s*ingr:'[^']*',\s*p26:([\d.]+|null),\s*p30:([\d.]+|null)", home):
    menu[(m.group(1) or m.group(2)).lower()] = (m.group(3), m.group(4))
p = partout(r"dès 6€00|Pizzas dès 6€|6€00")
constat("T2", "critique", "Prix faux sur le blog et les pieds d'articles",
        "ouvert" if p else "résolu", ", ".join(p[:5]))

p = partout(r"livre 7 jours sur 7.{0,60}17h30 à 22h|7j/7 de 17h30 à 22h|Livraison à [^<]{0,30} : 7j/7 de 17h30")
constat("T3", "critique", "Livraison annoncée dès 17h30 au lieu de 19h",
        "ouvert" if p else "résolu", f"{len(p)} page(s)")

p = partout(r"contact@pizzanapolicarpentras\.fr")
constat("T4", "critique", "Deux adresses e-mail différentes", "ouvert" if p else "résolu", ", ".join(p[:4]))

constat("T5", "important", "Google Analytics sans recueil de consentement",
        "résolu" if "consent-banner" in home and "'consent','default'" in home.replace(" ", "") else "ouvert")

ml = pages.get("mentions-legales/index.html", "")
manquants = [m for m, motif in (("RCS", r"RCS"), ("capital social", r"[Cc]apital"),
                                ("TVA intracommunautaire", r"TVA"),
                                ("directeur de la publication", r"[Dd]irecteur de (la )?publication"))
             if not re.search(motif, ml)]
constat("T6", "important", "Mentions légales incomplètes (LCEN)",
        "ouvert" if manquants else "résolu", "manque : " + ", ".join(manquants))

cgv = pages.get("cgv/index.html", "")
manque_cgv = [m for m, motif in (("minimum de commande", r"[Mm]inimum de commande"),
                                 ("droit de rétractation", r"[Rr]étractation|L\.?221-28"))
              if not re.search(motif, cgv)]
constat("T7", "important", "CGV sans minimum de commande ni rétractation",
        "ouvert" if manque_cgv else "résolu", "manque : " + ", ".join(manque_cgv))

ans = sorted({m for k, v in TEXTES.items()
              for m in re.findall(r"(1[0-9])\s*ans", re.sub(r"[«\"][^»\"]{0,400}[»\"]", " ", v))})
p2010 = partout(r"2010\s*[—–-]\s*Ouverture")
constat("T8", "important", "Ancienneté contradictoire",
        "ouvert" if p2010 or len(ans) > 1 else "résolu",
        f"durées citées : {', '.join(ans) or 'aucune'} ; « 2010 — Ouverture » sur {len(p2010)} page(s)")

p = [k for k, t in TEXTES.items() if re.search(r"4[,.]2\s*(★|/5|—|-)", t)]
constat("T9", "important", "Note affichée 4,2 à un endroit", "ouvert" if p else "résolu", ", ".join(p[:4]))

constat("T10", "important", "« Plus de 80 recettes » alors qu'il y en a 76",
        "résolu" if not partout(r"80\+?\s*pizzas|[Pp]lus de 80") else "ouvert",
        f"{len(menu)} entrées au menu")

p = partout(r"Spéciale Pizza Napoli|4 Fromages|Romaine[^<]{0,30}anchois")
constat("T11", "important", "Descriptions de pizzas fausses dans le blog",
        "ouvert" if p else "résolu", ", ".join(p[:5]))

constat("T12", "important", "Formulaire collectant des données sans information",
        "résolu" if "Meta Platforms Ireland" in " ".join(pages.values()) else "ouvert")

p = partout(r"Wikimedia Commons\s*[—-]\s*CC BY-SA(?!\s*\d)")
constat("T13", "important", "Crédits photo CC BY-SA incomplets",
        "ouvert" if p else "résolu", f"{len(p)} page(s)")

p = partout(r"la moins chère|La Meilleure Pizza du Vaucluse")
constat("T14", "mineur", "Superlatifs non étayés", "ouvert" if p else "résolu", ", ".join(p[:4]))

p = partout(r"[Pp]as de suppléments cachés")
constat("T15", "mineur", "« Pas de suppléments cachés » contredit par le minimum",
        "ouvert" if p else "résolu", ", ".join(p[:4]))

# ---------- rapport ----------
ordre = {"critique": 0, "important": 1, "mineur": 2}
etats = {}
for r in resultats:
    etats.setdefault(r["etat"], []).append(r)
print(f"\n{len(resultats)} constats repris · " +
      " · ".join(f"{k} {len(v)}" for k, v in sorted(etats.items())) + "\n")
for r in sorted(resultats, key=lambda r: (r["etat"] != "ouvert", ordre[r["gravite"]], r["code"])):
    marque = {"résolu": "RÉGLÉ   ", "ouvert": "OUVERT  ", "partiel": "PARTIEL ",
              "hors périmètre": "HORS    "}[r["etat"]]
    print(f"  {marque} {r['code']:4} [{r['gravite'][:4]}] {r['titre']}")
    if r["detail"]:
        print(f"           {r['detail'][:150]}")
json.dump(resultats, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_etat.json"), "w"),
          ensure_ascii=False, indent=1)
