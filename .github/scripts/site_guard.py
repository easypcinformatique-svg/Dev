#!/usr/bin/env python3
"""
Site guard — idempotent invariants for pizzanapolicarpentras.fr.
Run on every deploy + weekly. Derives truth from the repo itself, never from hardcoded values.

Invariants:
  1. Google rating/count identical everywhere (schema + visible text), source = homepage JSON-LD
  2. Single host (no www.) in every URL
  3. Canonical of each page = its own URL (except declared duplicates)
  4. Sitemap generated from files that exist on disk, lastmod from git history
  5. og:image and JSON-LD images point to files that exist
  6. <main> landmark, font-display=swap on every page
  7. foundingDate 2008 everywhere
  8. One Facebook URL
"""
import re, os, sys, glob, json, subprocess
from datetime import date
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from serres_page import CORPS as CORPS_SERRES, DESCRIPTION as DESC_SERRES

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
HOST = "https://pizzanapolicarpentras.fr"
FACEBOOK = "https://www.facebook.com/PizzaNapoliCarpentras/"
FOUNDED = "2008"
DUPLICATES = {  # page -> canonical target (content cannibalization)
    "livraison-pizza-84200": "livraison-pizza-carpentras",
    "pizza-carpentras": "pizzeria-carpentras",
}
EXCLUDE_FROM_SITEMAP = {"redirect", "404", "google", "mentions-legales-old", "photos-finales", "photos-preview"}
CONTROL_LABELS = {"size-select": "Taille de la pizza", "qty-select": "Quantité"}
STRUCTURAL = ("div", "nav", "main", "header", "footer", "section", "ul", "table")


def _gal(src, emoji, alt, extra="", style=""):
    return (f'<div class="gal-item"{extra}><img src="{src}" srcset="{src}" alt="{alt}" '
            f'loading="lazy"{style}><div class="gal-overlay"><span>{emoji}</span></div></div>')


GALLERY = '<div class="galerie-grid"> ' + " ".join([
    _gal("20250425_192921.jpg", "🌿", "Pizza Milano courgettes Pizza Napoli Carpentras"),
    _gal("20230926_202527.jpg", "🍕", "Pizza artisanale Pizza Napoli Carpentras"),
    _gal("saint-jacques-.webp", "🌊", "Pizza Saint Jacques fruits de mer Carpentras",
         ' style="overflow:hidden;"',
         ' style="object-fit:cover;width:100%;height:100%;transform:rotate(90deg) scale(2.2);'
         'transform-origin:center center;"'),
    _gal("20240123_201507.jpg", "🍕", "Pizza Mozza di Bufala jambon Carpentras"),
    _gal("20230926_203901.jpg", "🌿", "Pizza Végétarienne champignons Carpentras"),
]) + " </div>"
# Must stay in step with getMinPizzasForCity() in the order form.
DELIVERY_ANSWER = (
    "sur Carpentras et les communes environnantes, "
    "tous les soirs de 19h00 à 22h00 (commandes dès 17h30). Le minimum varie selon la commune : "
    "2 grandes pizzas (ou 4 petites) sur Carpentras et Serres, 3 sur Pernes-les-Fontaines, Monteux, "
    "Aubignan, Loriol-du-Comtat et Caromb, 4 sur Mazan et Saint-Didier. Appelez le 07 61 08 36 08."
)
IMG_EXT = (".webp", ".png", ".jpg", ".jpeg", ".svg", ".gif")
# The address that answers: it is the one on the legal pages.
EMAIL = "carpentraspizzanapoli@gmail.com"
GA4 = ('<script async src="https://www.googletagmanager.com/gtag/js?id=G-T2QW447J8J"></script>\n'
       "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
       "gtag('js',new Date());gtag('config','G-T2QW447J8J');</script>")

# Testimonials named pizzas by Italian names the menu does not use.
MENU_ALIASES = {"Quattro Formaggi": "4 Fro", "Regina": "Reine"}

# A generator transliterated the guides to ASCII. Only words whose unaccented
# form is not itself a French word are listed here — "reste", "marche", "cote"
# and "ou" are real words and must never be rewritten blindly.
ACCENTS = {
    "chateau": "château", "chateaux": "châteaux", "medieval": "médiéval",
    "medievale": "médiévale", "medievaux": "médiévaux", "medievales": "médiévales",
    "siecle": "siècle", "siecles": "siècles", "tres": "très", "apres": "après",
    "decouverte": "découverte", "decouvertes": "découvertes", "decouvrez": "découvrez",
    "decouvrir": "découvrir", "fete": "fête", "fetes": "fêtes", "eglise": "église",
    "eglises": "églises", "region": "région", "regions": "régions", "arreter": "arrêter",
    "arrete": "arrête", "musee": "musée", "musees": "musées", "palir": "pâlir",
    "legales": "légales", "legale": "légale", "confidentialite": "confidentialité",
    "donnees": "données", "numero": "numéro", "duree": "durée",
    "provencal": "provençal", "provencale": "provençale", "provencaux": "provençaux",
    "provencales": "provençales", "cathedrale": "cathédrale", "celebre": "célèbre",
    "celebres": "célèbres", "specialite": "spécialité", "specialites": "spécialités",
    "reputee": "réputée", "repute": "réputé", "reputees": "réputées",
    "developpe": "développé", "proximite": "proximité", "qualite": "qualité",
    "qualites": "qualités", "atmosphere": "atmosphère", "ete": "été", "etait": "était",
    "meme": "même", "memes": "mêmes", "creee": "créée", "cree": "créé",
    "situee": "située", "situe": "situé", "realise": "réalisé", "interet": "intérêt",
    "elegant": "élégant", "elegante": "élégante", "precede": "précédé",
    "veritable": "véritable", "veritables": "véritables", "authentique": "authentique",
    "etablissement": "établissement", "evenement": "événement", "evenements": "événements",
    "cle": "clé", "the": "thé", "annee": "année", "annees": "années",
    "quartier": "quartier", "acces": "accès", "succes": "succès", "proces": "procès",
    "chateauneuf": "châteauneuf", "hotel": "hôtel", "hotels": "hôtels",
    "foret": "forêt", "forets": "forêts", "riviere": "rivière", "rivieres": "rivières",
    "riche": "riche", "prefere": "préféré", "preferee": "préférée",
    "reserve": "réservé", "reservee": "réservée", "reservation": "réservation",
    "specialement": "spécialement", "generalement": "généralement",
    "particulierement": "particulièrement", "premiere": "première", "dernier": "dernier",
    "derniere": "dernière", "entiere": "entière", "maniere": "manière",
    "lumiere": "lumière", "priere": "prière", "carriere": "carrière",
    "frontiere": "frontière", "barriere": "barrière", "cimetiere": "cimetière",
}
# Ambiguous words, disambiguated by their surroundings.
ACCENTS_CONTEXTE = {
    r'\bpres de\b': "près de", r'\bPres de\b': "Près de",
    r"\bCote d'Azur\b": "Côte d'Azur",
    r'\ble marche\b': "le marché", r'\bdu marche\b': "du marché",
    r'\bau marche\b': "au marché", r'\bLe marche\b': "Le marché",
    r'\bmarche provencal\b': "marché provençal", r'\bmarche hebdomadaire\b': "marché hebdomadaire",
    r'\bmarches provencaux\b': "marchés provençaux", r'\bmarches de Noel\b': "marchés de Noël",
    r'\bNoel\b': "Noël",
}

report = []

def log(page, msg):
    report.append(f"[{page}] {msg}")
    print(f"  [{page}] {msg}")

def exists_local(ref, base_dir):
    if not ref or ref.startswith(("http", "data:", "//")):
        return True
    ref = ref.split("?")[0].split("#")[0]
    return os.path.exists(os.path.join(base_dir, ref)) or os.path.exists(os.path.join(SITE, ref.lstrip("/")))

def repair_ref(ref, base_dir):
    """Missing local image: try sibling extensions and dropping an /img/ segment."""
    stem, ext = os.path.splitext(ref)
    candidates = [stem + e for e in IMG_EXT if e != ext]
    if "/img/" in ref:
        alt = ref.replace("/img/", "/")
        candidates += [alt] + [os.path.splitext(alt)[0] + e for e in IMG_EXT]
    for cand in candidates:
        if exists_local(cand, base_dir):
            return cand
    return None

_tailles = {}

def mesurer(ref, base_dir):
    """Pixel size of a local image, read once and cached."""
    if not ref or ref.startswith(("http", "data:", "//")):
        return None
    ref = ref.split("?")[0].split("#")[0]
    for chemin in (os.path.join(base_dir, ref), os.path.join(SITE, ref.lstrip("/"))):
        if chemin in _tailles:
            return _tailles[chemin]
        if os.path.exists(chemin):
            try:
                from PIL import Image
                with Image.open(chemin) as im:
                    _tailles[chemin] = im.size
                    return im.size
            except Exception:
                _tailles[chemin] = None
    return None


def page_url(path):
    rel = os.path.relpath(path, SITE).replace(os.sep, "/")
    if rel == "index.html":
        return f"{HOST}/"
    if rel.endswith("/index.html"):
        return f"{HOST}/{rel[:-len('index.html')]}"
    return f"{HOST}/{rel}"

def is_shallow():
    try:
        return subprocess.run(["git", "-C", SITE, "rev-parse", "--is-shallow-repository"],
                              capture_output=True, text=True, timeout=20).stdout.strip() == "true"
    except Exception:
        return True

SHALLOW = is_shallow()

def git_lastmod(path):
    # A shallow clone truncates history and would date every file "today",
    # churning the sitemap on each run. Fall back to the published date instead.
    if SHALLOW:
        return None
    try:
        out = subprocess.run(["git", "-C", SITE, "log", "-1", "--format=%cs", "--", os.path.relpath(path, SITE)],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        return out or None
    except Exception:
        return None

# ---------- source of truth: homepage rating ----------
home = os.path.join(SITE, "index.html")
with open(home, encoding="utf-8") as f:
    home_html = f.read()
m_r = re.search(r'"ratingValue":"([\d.]+)"', home_html)
m_c = re.search(r'"reviewCount":"(\d+)"', home_html)
if not (m_r and m_c):
    print("FATAL: homepage has no AggregateRating"); sys.exit(1)
RATING, COUNT = m_r.group(1), m_c.group(1)
RATING_COMMA = RATING.replace(".", ",")

# ---------- source of truth: the menu itself ----------
_menu = re.search(r'const PIZZAS\s*=\s*\[(.*?)\];', home_html, re.DOTALL)
MENU = {}
for _n, _p26, _p30 in re.findall(r"name:'([^']+)'.*?p26:([\d.]+|null),p30:([\d.]+|null)", _menu.group(1)):
    MENU[_n.lower()] = (None if _p26 == "null" else float(_p26),
                        None if _p30 == "null" else float(_p30))
MIN_PRICE = min(p for p26, p30 in MENU.values() for p in (p26,) if p)


def euro(p):
    return f"{int(p)}€" if abs(p - int(p)) < 0.005 else f"{int(p)}€{round((p - int(p)) * 100):02d}"


print(f"Source of truth: {RATING}/5 — {COUNT} avis · {len(MENU)} pizzas, dès {euro(MIN_PRICE)}\n")

# ---------- per-page invariants ----------
pages = sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True))
for path in pages:
    rel = os.path.relpath(path, SITE).replace(os.sep, "/")
    if rel.split("/")[0] in EXCLUDE_FROM_SITEMAP:
        continue
    with open(path, encoding="utf-8") as f:
        c = f.read()
    orig = c
    base_dir = os.path.dirname(path)

    # 1. rating everywhere
    c = re.sub(r'"ratingValue":"[\d.]+"', f'"ratingValue":"{RATING}"', c)
    c = re.sub(r'"reviewCount":"\d+"', f'"reviewCount":"{COUNT}"', c)
    c = re.sub(r'\b[1-5],\d\s*/\s*5\b', f'{RATING_COMMA}/5', c)
    c = re.sub(r'\b[1-5]\.\d\s*/\s*5\b(?![\d"])', f'{RATING}/5', c)
    c = re.sub(r'\bnote\s+[1-5][,.]\d\b', f'note {RATING_COMMA}', c)
    c = re.sub(r'\b\d{3}\s+avis\b', f'{COUNT} avis', c)
    c = re.sub(r'animCounter\(r,[\d.]+,', f'animCounter(r,{RATING},', c)
    c = re.sub(r'(data-target=")\d+(">0</span><span class="counter-lbl">Avis Google)', rf'\g<1>{COUNT}\2', c)

    # 2. single host
    c = c.replace("https://www.pizzanapolicarpentras.fr", HOST).replace("http://pizzanapolicarpentras.fr", HOST)

    # 2b. years of experience, derived from the founding year so it never goes stale
    years = date.today().year - int(FOUNDED)
    # The optional backslash also repairs a bad \' escape left inside JSON-LD.
    c = re.sub(r'\b\d{1,2}(\s*)ans(\s*)d\\?[\'’]exp[ée]rience',
               rf"{years}\1ans\2d'expérience", c)

    # 2c. the delivery minimum varies by town; no page may promise the lowest one
    # for towns that need more, or the order form rejects a customer it invited.
    c = re.sub(
        r'dès 2 grandes pizzas commandées sur Carpentras et communes environnantes[^"<]*?'
        r'Appelez le 07 61 08 36 08\.',
        DELIVERY_ANSWER, c)

    # 2d. delivery runs 19h-22h; orders are taken from 17h30. Don't conflate the two.
    c = c.replace("livraison à domicile est disponible tous les jours de 17h30 à 22h",
                  "livraison à domicile est disponible tous les jours de 19h00 à 22h00")

    # 3. canonical = own URL (or duplicate target)
    seg = rel.split("/")[0] if rel.endswith("/index.html") and rel != "index.html" else None
    target = f"{HOST}/{DUPLICATES[seg]}/" if seg in DUPLICATES else page_url(path)
    if 'rel="canonical"' in c:
        c = re.sub(r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="{target}"', c)
    elif "</head>" in c:
        c = c.replace("</head>", f'<link rel="canonical" href="{target}">\n</head>', 1)
    if seg not in DUPLICATES:
        c = re.sub(r'(<meta property="og:url" content=")[^"]*"', rf'\g<1>{target}"', c)

    # 5. images must exist
    m = re.search(r'<meta property="og:image" content="([^"]+)"', c)
    if m:
        ref = m.group(1).replace(HOST + "/", "")
        if not exists_local(ref, base_dir):
            c = c.replace(m.group(0), f'<meta property="og:image" content="{HOST}/hero1.webp">')
            log(rel, f"og:image {ref} introuvable -> hero1.webp")
    for img in set(re.findall(r'"' + re.escape(HOST) + r'/([^"]+\.(?:png|jpg|jpeg|webp))"', c)):
        if not exists_local(img, base_dir):
            fixed = repair_ref(img, base_dir) or "hero1.webp"
            c = c.replace(f'"{HOST}/{img}"', f'"{HOST}/{fixed}"')
            log(rel, f"image JSON-LD {img} introuvable -> {fixed}")
    # no hotlinked external images: a third-party URL can rot without warning
    for tag in set(re.findall(r'<img\s[^>]*>', c)):
        src = re.search(r'src="([^"]+)"', tag)
        if src and src.group(1).startswith(("http://", "https://")) and not src.group(1).startswith(HOST):
            c = c.replace(tag, "")
            log(rel, f"<img> externe retirée ({src.group(1).split('/')[2]})")
    for tag in set(re.findall(r'<img\s[^>]*>', c)):
        src = re.search(r'src="([^"]+)"', tag)
        if src and not exists_local(src.group(1), base_dir):
            fixed = repair_ref(src.group(1), base_dir)
            if fixed:
                c = c.replace(tag, tag.replace(f'src="{src.group(1)}"', f'src="{fixed}"'))
                if "srcset=" in tag:
                    c = c.replace(f'srcset="{src.group(1)}"', f'srcset="{fixed}"')
                log(rel, f"<img {src.group(1)}> introuvable -> réparé en {fixed}")
            else:
                # Never delete markup: an earlier one-shot script removed <img> tags
                # with a regex that also swallowed their opening <div>, leaving four
                # orphan </div> and a collapsed gallery. Report, don't cut.
                log(rel, f"ALERTE <img {src.group(1)}> introuvable et irréparable")

    # 6. landmark + fonts
    if "<main" not in c:
        anchor = re.search(r'</nav>|</header>|<body[^>]*>', c)
        if anchor:
            c = c[:anchor.end()] + '\n<main id="main-content">' + c[anchor.end():]
            c = c.replace("<footer", "</main>\n<footer", 1) if "<footer" in c else c.replace("</body>", "</main>\n</body>", 1)
            log(rel, "<main> ajouté")
    c = re.sub(r'(fonts\.googleapis\.com/css2\?[^"]*?)(?<!display=swap)"', lambda mm: mm.group(1) + ("" if "display=swap" in mm.group(1) else "&display=swap") + '"', c)

    # 6b. every form control needs an accessible name; a placeholder is not one
    def name_control(m):
        tag = m.group(0)
        cid = re.search(r'id="([^"]+)"', tag)
        if re.search(r'\b(aria-label|aria-labelledby|title)=', tag):
            return tag
        if cid and f'for="{cid.group(1)}"' in c:
            return tag
        ph = re.search(r'placeholder="([^"]+)"', tag)
        cls = re.search(r'class="([^"]*)"', tag)
        if ph:
            label = ph.group(1).rstrip("…. ")
        elif cls and (known := next((v for k, v in CONTROL_LABELS.items() if k in cls.group(1)), None)):
            label = known  # controls built in JS templates, with no placeholder to borrow
        else:
            return tag
        log(rel, f'champ {cid.group(1) if cid else "?"} sans nom accessible -> aria-label="{label}"')
        return tag[:-1].rstrip() + f' aria-label="{label}"' + tag[-1]

    c = re.sub(r'<(?:input|select|textarea)\s[^>]*>', name_control, c)

    # 6c. titles: strip redundancy only (brand stated twice, decorative lists).
    # Google truncates past ~65 chars. Nothing here removes a keyword.
    def trim_title(m):
        t = old = m.group(1)
        if t.count("Pizza Napoli") > 1:
            t = re.sub(r'\s*[|—-]\s*Pizza Napoli Carpentras\s*$', '', t)
        t = t.replace("Sorties, Patrimoine + Pizza", "Sorties &amp; Pizza")
        t = t.replace("Patrimoine, Marchés, Sorties + Pizza", "Marchés, Sorties &amp; Pizza")
        t = re.sub(r'\s*\|\s*7j/7 dès 19h\s*$', '', t)
        t = re.sub(r'\s*\|\s*Pizza Napoli\s*—\s*Pâte Maison dès 7€90\s*$', ' | Pizza Napoli', t)
        t = re.sub(r'\s*\|\s*La Meilleure Pizza du Vaucluse depuis 2008\s*$', ' | Depuis 2008', t)
        t = re.sub(r'\s{2,}', ' ', t).strip(" |—-")
        # Measure what the reader sees: &amp; is one character, not five.
        shown, was = len(unescape(t)), len(unescape(old))
        if t != old and shown <= 65:
            log(rel, f"title {was} -> {shown} car.")
            return f"<title>{t}</title>"
        return m.group(0)

    c = re.sub(r'<title>([^<]*)</title>', trim_title, c)

    # 6e. prices quoted in prose must match the menu
    c = re.sub(r'dès\s*\d+\s*€\s*\d{0,2}', f'dès {euro(MIN_PRICE)}', c)
    c = re.sub(r'[Pp]izzas? dès \d+\s*€\s*\d{0,2}', f'Pizzas dès {euro(MIN_PRICE)}', c)

    def fix_card(m):
        nom, prix = m.group(1), m.group(2)
        p26, p30 = MENU.get(nom.lower(), (None, None))
        if p30 is None:
            return m.group(0)
        vrai = f"{euro(p26)} / {euro(p30)}" if p26 else f"{euro(p30)} grande"
        if vrai != prix:
            log(rel, f"prix {nom} : {prix} -> {vrai}")
        return m.group(0).replace(f'>{prix}<', f'>{vrai}<')

    c = re.sub(r'<div class="pizza-name">([^<]+)</div>'
               r'<div class="pizza-desc">[^<]*</div>'
               r'<div class="pizza-price">([^<]+)</div>', fix_card, c)

    # 6f. testimonials may only name pizzas that exist on the menu
    for faux, vrai in MENU_ALIASES.items():
        if faux in c:
            c = c.replace(faux, vrai)
            log(rel, f"avis : « {faux} » absente de la carte -> « {vrai} »")

    # 6g. the CTA opens the online form before 17h30 and the phone modal after,
    # so it must not promise one channel.
    c = c.replace("🍕 Commander par WhatsApp", "🍕 Commander")

    # 6h. accents dropped by a generator that transliterated to ASCII.
    # Text nodes only: attributes carry file names and URLs, and accenting
    # img/chateau.webp into img/château.webp breaks the image.
    def accentuer(texte):
        for sans, avec in ACCENTS.items():
            texte = re.sub(rf'\b{sans}\b', avec, texte)
            texte = re.sub(rf'\b{sans.capitalize()}\b', avec.capitalize(), texte)
        for motif, remplacement in ACCENTS_CONTEXTE.items():
            texte = re.sub(motif, remplacement, texte)
        return texte

    morceaux = re.split(r'(<[^>]*>)', c)
    dans_script = False
    doublons = 0
    for i, bout in enumerate(morceaux):
        if bout.startswith("<"):
            nom = re.match(r'</?\s*([a-zA-Z][a-zA-Z0-9]*)', bout)
            if not nom:
                continue  # "i+1<n" and friends: not a tag
            if nom.group(1).lower() in ("script", "style"):
                dans_script = not bout.startswith("</")
            elif not dans_script and re.search(r'\b([\w-]+)="[^"]*"[^>]*\s\1=', bout):
                morceaux[i] = dedupe(re.match(r'.*', bout, re.DOTALL))
                doublons += 1
            continue
        if not dans_script:
            morceaux[i] = accentuer(bout)
    c = "".join(morceaux)
    if doublons:
        log(rel, f"{doublons} balise(s) avec attribut dupliqué corrigée(s)")

    # 6i. Serres: the article described Serres (05700) in the Hautes-Alpes,
    # 150 km outside the delivery zone, while promising delivery there.
    # The Serres we serve is the hamlet of Carpentras (84200).
    if rel == "blog/que-faire-serres-ce-soir/index.html" and "Hautes-Alpes" in c:
        i, j = c.find("<h1>"), c.find('<h2>À lire aussi')
        if i != -1 and j != -1:
            fin = c.rfind("</div>", i, j)
            fin = c.rfind('<div class="cta-box"', i, j)
            fin = fin if fin != -1 else j
            c = c[:i] + CORPS_SERRES + c[fin:]
            c = re.sub(r'(<meta name="description" content=")[^"]*"', rf'\g<1>{DESC_SERRES}"', c)
            c = re.sub(r'(<meta property="og:description" content=")[^"]*"', rf'\g<1>{DESC_SERRES}"', c)
            c = c.replace("Serre-Ponçon", "Comtat Venaissin").replace("Hautes-Alpes", "Vaucluse")
            c = c.replace("05700", "84200")
            log(rel, "article réécrit sur Serres (84200), hameau de Carpentras")

    # 6j. measurement was on the homepage only, so 44 pages reported nothing
    if "googletagmanager" not in c and "</head>" in c and "noindex" not in (
            re.search(r'<meta name="robots" content="([^"]*)"', c) or type("", (), {"group": lambda s, i: ""})()).group(1):
        c = c.replace("</head>", GA4 + "\n</head>", 1)
        log(rel, "GA4 ajouté (page non mesurée)")

    # 6k. a page with no description lets Google invent one
    if 'name="description"' not in c and "</head>" in c:
        titre = re.search(r'<title>([^<]*)</title>', c)
        resume = unescape(titre.group(1)).split("|")[0].strip() if titre else "Pizza Napoli Carpentras"
        c = c.replace("</head>", f'<meta name="description" content="{resume} — Pizza Napoli Carpentras, '
                                 f'pizzeria artisanale depuis 2008. Livraison 7j/7. ☎ 07 61 08 36 08">\n</head>', 1)
        log(rel, "meta description ajoutée")

    # 6l. an attribute written twice is invalid; the second one is ignored
    def dedupe(m):
        tag = m.group(0)
        debut = re.match(r'<\w+', tag).group(0)
        corps = tag[len(debut):].rstrip(">").rstrip("/")
        vus, sortie = set(), []
        # Boolean attributes (itemscope, async, checked) carry no value and
        # must survive: dropping itemscope silently breaks the microdata.
        for att in re.finditer(r'([\w-]+)(?:="[^"]*")?', corps):
            if not att.group(1) or att.group(1) in vus:
                continue
            vus.add(att.group(1)); sortie.append(att.group(0))
        ferme = "/>" if tag.rstrip(">").endswith("/") else ">"
        return f"{debut} {' '.join(sortie)}{ferme}" if sortie else tag

    # Applied during the tag walk below, never with a bare regex over the whole
    # document: "i+1<n" inside a script reads as a tag opening and a pass like
    # this one shredded the order form's JavaScript.

    # 6m. the <main> target existed but no link ever pointed at it
    if "<main" in c and 'id="main-content"' not in c:
        c = re.sub(r'<main(?![^>]*\bid=)', '<main id="main-content"', c, count=1)
    if 'href="#main-content"' not in c and "<body" in c and 'id="main-content"' in c:
        c = re.sub(r'(<body[^>]*>)',
                   r'\1\n<a href="#main-content" class="skip-link">Aller au contenu</a>', c, count=1)
        log(rel, "lien d'évitement ajouté")

    # 6n. one contact address; the schema pointed at a second one
    c = c.replace("contact@pizzanapolicarpentras.fr", EMAIL)

    # 6o. the card holds 80 recipes, of which seven are desserts
    c = re.sub(r'\b80\s*\+?\s*pizzas\b', "80 recettes", c)
    c = re.sub(r'\b80\+\s*recettes\b', "80 recettes", c)

    # 6p. images without width/height shift the layout as they load (CLS),
    # and the first image of a page is its LCP candidate, so it must not wait
    # for lazy loading.
    premiere = [True]
    def dimensionner(m):
        tag, src = m.group(0), re.search(r'src="([^"]+)"', m.group(0))
        if not src:
            return tag
        if "width=" not in tag or "height=" not in tag:
            taille = mesurer(src.group(1), base_dir)
            if taille:
                tag = tag[:-1].rstrip() + f' width="{taille[0]}" height="{taille[1]}">'
        if premiere[0]:
            premiere[0] = False
            tag = tag.replace(' loading="lazy"', ' loading="eager" fetchpriority="high"')
        return tag

    avant_img = c
    c = re.sub(r'<img\s[^>]*>', dimensionner, c)
    if c != avant_img:
        log(rel, "dimensions d'images / priorité LCP")

    # 6q. social cards: a share with no image is a share nobody clicks
    if "</head>" in c:
        titre = re.search(r'<title>([^<]*)</title>', c)
        desc = re.search(r'<meta name="description" content="([^"]*)"', c)
        ajouts = []
        if "og:image" not in c:
            ajouts.append(f'<meta property="og:image" content="{HOST}/hero1.webp">')
        if "og:type" not in c:
            ajouts.append('<meta property="og:type" content="article">')
        if "og:site_name" not in c:
            ajouts.append('<meta property="og:site_name" content="Pizza Napoli Carpentras">')
        if "og:locale" not in c:
            ajouts.append('<meta property="og:locale" content="fr_FR">')
        if "twitter:card" not in c:
            ajouts.append('<meta name="twitter:card" content="summary_large_image">')
            ajouts.append(f'<meta name="twitter:image" content="{HOST}/hero1.webp">')
            if titre:
                ajouts.append(f'<meta name="twitter:title" content="{titre.group(1)}">')
            if desc:
                ajouts.append(f'<meta name="twitter:description" content="{desc.group(1)}">')
        if ajouts:
            c = c.replace("</head>", "\n".join(ajouts) + "\n</head>", 1)
            log(rel, f"{len(ajouts)} balise(s) sociale(s) ajoutée(s)")

    # 6r. a breadcrumb with a single item is not shown by Google. On the
    # homepage there is nothing to lead back to, so drop it entirely.
    if rel == "index.html" and "BreadcrumbList" in c and c.count('"ListItem"') < 2:
        c = re.sub(r'<script type="application/ld\+json">\{[^<]*BreadcrumbList[^<]*\}</script>\s*', '', c)
        log(rel, "fil d'Ariane à un seul niveau retiré")
    if rel != "index.html" and ("BreadcrumbList" not in c or c.count('"ListItem"') < 2):
        chemin = rel[:-len("/index.html")] if rel.endswith("/index.html") else rel[:-len(".html")]
        miettes = [("Accueil", f"{HOST}/")]
        if chemin.startswith("blog/") or chemin == "blog":
            miettes.append(("Blog", f"{HOST}/blog/"))
        if chemin not in ("blog",):
            nom = unescape(re.search(r'<h1[^>]*>(.*?)</h1>', c, re.DOTALL).group(1)) if re.search(r'<h1', c) else chemin
            nom = re.sub(r'<[^>]+>', ' ', nom).strip()[:70]
            miettes.append((nom, page_url(path)))
        fil = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(miettes)]}
        bloc = '<script type="application/ld+json">' + json.dumps(fil, ensure_ascii=False) + '</script>'
        if "BreadcrumbList" in c:
            c = re.sub(r'<script type="application/ld\+json">\{[^<]*BreadcrumbList[^<]*\}</script>', bloc, c)
        else:
            c = c.replace("</head>", bloc + "\n</head>", 1)
        log(rel, "fil d'Ariane structuré")

    # 6d. repair damage left by earlier one-shot scripts
    if '<div class="galerie-grid"> </div>' in c:
        i = c.find('<div class="galerie-grid">')
        j = c.find('<div style="text-align:center;padding:1rem;font-size:.75rem', i)
        if i != -1 and j != -1:
            c = c[:i] + GALLERY + "\n" + c[j:]
            log(rel, "galerie reconstruite (4 vignettes perdues par un script)")
    # 6s. Sarrians: the stub redirected with setTimeout, which Google reads as
    # a soft redirect and which fails WCAG 2.2.1 (no adjustable time limit).
    # Ten pages link here, so it must be a real page, not a trap door.
    if rel == "livraison-pizza-sarrians/index.html" and "setTimeout" in c:
        c = re.sub(r'<script>\s*setTimeout\([^<]*?</script>', '', c, flags=re.DOTALL)
        log(rel, "redirection JavaScript temporisée supprimée")

    if "</nav>rsaquo;" in c:
        n = c.count("</nav>rsaquo;")
        c = c.replace("</nav>rsaquo;", "&rsaquo;")
        log(rel, f"fil d'Ariane : {n}× '</nav>rsaquo;' -> '&rsaquo;'")

    # 7. founding date
    c = re.sub(r'"foundingDate":"\d{4}"', f'"foundingDate":"{FOUNDED}"', c)
    c = re.sub(r'\b(depuis|en|dès|fondée? en|créée? en)\s+2010\b', rf'\1 {FOUNDED}', c, flags=re.IGNORECASE)

    # 8. one facebook
    c = re.sub(r'https?://(?:www\.)?facebook\.com/(?:pizzanapolipizzeria|PizzaNapoliCarpentras)/?', FACEBOOK, c)

    if c != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        log(rel, "normalisée")

# ---------- custom 404 ----------
# GitHub Pages serves its own English "Page not found" otherwise: no branding,
# no navigation, no phone number.
page404 = os.path.join(SITE, "404.html")
if not os.path.exists(page404):
    with open(page404, "w", encoding="utf-8") as f:
        f.write(f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, follow">
<title>Page introuvable — Pizza Napoli Carpentras</title>
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#FFFDF7;color:#3D3328;
display:flex;min-height:100vh;align-items:center;justify-content:center;padding:24px;}}
.b{{max-width:540px;text-align:center;}}
h1{{font-size:clamp(1.6rem,5vw,2.2rem);margin:0 0 .6rem;color:#A8202A;}}
p{{line-height:1.7;color:#5A5248;}}
.l{{display:flex;flex-wrap:wrap;gap:.7rem;justify-content:center;margin-top:1.8rem;}}
a{{padding:.75rem 1.4rem;border:2px solid #C8972A;border-radius:2px;color:#3D3328;
text-decoration:none;font-size:.82rem;letter-spacing:.08em;text-transform:uppercase;}}
a.p{{background:#A8202A;border-color:#A8202A;color:#fff;}}
</style></head>
<body><main class="b">
<p style="font-size:3rem;margin:0;">🍕</p>
<h1>Cette page n'existe pas</h1>
<p>Le lien est peut-être ancien, ou l'adresse comporte une erreur.
Notre carte, elle, est toujours là — et le four tourne 7&nbsp;j/7 dès 17h30.</p>
<div class="l">
<a class="p" href="{HOST}/">Retour à l'accueil</a>
<a href="{HOST}/#menu">Voir la carte</a>
<a href="tel:0761083608">07 61 08 36 08</a>
</div></main></body></html>
''')
    print("  [404.html] page d'erreur personnalisée créée")

# ---------- 4. sitemap from disk ----------
smap = os.path.join(SITE, "sitemap.xml")
published = {}
if os.path.exists(smap):
    prev = open(smap, encoding="utf-8").read()
    published = dict(re.findall(r'<loc>(.*?)</loc>\s*<lastmod>(.*?)</lastmod>', prev, re.DOTALL))

entries = []
for path in pages:
    rel = os.path.relpath(path, SITE).replace(os.sep, "/")
    top = rel.split("/")[0]
    if top in EXCLUDE_FROM_SITEMAP or rel == "404.html":
        continue
    if not (rel == "index.html" or rel.endswith("/index.html") or rel.startswith("blog/")):
        continue
    seg = top if rel.endswith("/index.html") and rel != "index.html" else None
    if seg in DUPLICATES:
        continue
    # A page asking not to be indexed must not also be submitted for indexing;
    # Search Console reports the pair as "excluded by noindex tag".
    robots = re.search(r'<meta name="robots" content="([^"]*)"', open(path, encoding="utf-8").read())
    if robots and "noindex" in robots.group(1):
        print(f"  [sitemap.xml] {rel} en noindex -> exclue")
        continue
    url = page_url(path)
    if url == f"{HOST}/":
        prio, freq = "1.0", "daily"
    elif "/blog/" in url:
        prio, freq = "0.6", "monthly"
    else:
        prio, freq = "0.8", "weekly"
    entries.append((url, git_lastmod(path) or published.get(url) or "2026-09-11", freq, prio))

entries.sort(key=lambda e: (e[0] != f"{HOST}/", "/blog/" in e[0], e[0]))
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for url, lastmod, freq, prio in entries:
    xml += ["  <url>", f"    <loc>{url}</loc>", f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{freq}</changefreq>", f"    <priority>{prio}</priority>", "  </url>"]
xml.append("</urlset>\n")
new_sitemap = "\n".join(xml)
old = open(smap, encoding="utf-8").read() if os.path.exists(smap) else ""
if old != new_sitemap:
    with open(smap, "w", encoding="utf-8") as f:
        f.write(new_sitemap)
    log("sitemap.xml", f"régénéré depuis le disque : {len(entries)} URLs")

print(f"\n{len(report)} changement(s)" if report else "\nAucun changement — site conforme")

# ---------- structural check: fail loudly rather than ship broken markup ----------
# The guard used to verify presence only, so it happily approved a page whose
# <main> held four orphan </div> and whose <nav> was closed three times.
broken = []
for path in pages:
    rel = os.path.relpath(path, SITE).replace(os.sep, "/")
    if rel.split("/")[0] in EXCLUDE_FROM_SITEMAP:
        continue
    with open(path, encoding="utf-8") as f:
        c = f.read()
    for tag in STRUCTURAL:
        opened = len(re.findall(rf'<{tag}[\s>]', c))
        closed = c.count(f"</{tag}>")
        if opened != closed:
            broken.append(f"{rel}: <{tag}> ouvert {opened}× fermé {closed}×")

if broken:
    print(f"\nSTRUCTURE HTML INVALIDE — {len(broken)} anomalie(s) :")
    for b in broken:
        print(f"  {b}")
    sys.exit(1)
print("Structure HTML équilibrée sur toutes les pages")
