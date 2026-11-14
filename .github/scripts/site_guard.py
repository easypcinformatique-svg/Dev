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
import re, os, sys, glob, json, shutil, subprocess, unicodedata
from datetime import date
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from serres_page import CORPS as CORPS_SERRES, DESCRIPTION as DESC_SERRES

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
HOST = "https://pizzanapolicarpentras.fr"
# The printed flyer is the menu customers hold, so it is the reference for
# recipes and prices. Extracted from the October 2026 edition; see carte.json.
CARTE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "data", "carte.json"), encoding="utf-8"))
# Company identity as the registry holds it (RCS Avignon, RNE, Insee, BODACC).
# The legal pages are built from this rather than retyped.
ENTREPRISE = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "data", "entreprise.json"), encoding="utf-8"))
FACEBOOK = "https://www.facebook.com/PizzaNapoliCarpentras/"
FOUNDED = "2008"
DUPLICATES = {  # page -> canonical target (content cannibalization)
    "livraison-pizza-84200": "livraison-pizza-carpentras",
    "pizza-carpentras": "pizzeria-carpentras",
}
EXCLUDE_FROM_SITEMAP = {"redirect", "404", "google", "mentions-legales-old", "photos-finales", "photos-preview"}
CONTROL_LABELS = {"size-select": "Taille de la pizza", "qty-select": "Quantité"}
# slug -> (nom, code postal, minimum de pizzas, slug du guide).
# Les minimums doivent rester alignés sur getMinPizzasForCity().
COMMUNES = {
    "carpentras": ("Carpentras", "84200", 2, "carpentras"),
    "serres": ("Serres", "84200", 2, "serres"),
    "monteux": ("Monteux", "84170", 3, "monteux"),
    "aubignan": ("Aubignan", "84810", 3, "aubignan"),
    "mazan": ("Mazan", "84380", 4, "mazan"),
    "loriol-du-comtat": ("Loriol-du-Comtat", "84870", 4, "loriol"),
    "caromb": ("Caromb", "84330", 4, "caromb"),
    "pernes-les-fontaines": ("Pernes-les-Fontaines", "84210", 5, "pernes"),
    "saint-didier": ("Saint-Didier", "84210", 5, "saint-didier"),
}
# Monteux village is 3, the lake area and the outskirts are 4. An address
# string cannot tell them apart, so the form applies 3 — it never turns away a
# village order — and the zone table on the homepage states both, the team
# settling the case on the call back.
SECTEURS = {("monteux", "lac / périphérie"): 4}
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
# Derived from COMMUNES so the answer can never drift from the form's own
# rule, which is itself generated from the same table (see rule 6z).
def _liste(noms):
    return noms[0] if len(noms) == 1 else ", ".join(noms[:-1]) + " et " + noms[-1]


_paliers = {}
for _slug, (_nom, _cp, _mini, _guide) in COMMUNES.items():
    _paliers.setdefault(_mini, []).append(_nom)
_bouts = []
for _i, _mini in enumerate(sorted(_paliers)):
    _quoi = f"{_mini} grandes pizzas (ou {_mini * 2} petites)" if _i == 0 else str(_mini)
    _bouts.append(f"{_quoi} sur {_liste(_paliers[_mini])}")
DELIVERY_ANSWER = (
    "sur Carpentras et les communes environnantes, "
    "tous les soirs de 19h00 à 22h00 (commandes dès 17h30). Le minimum varie selon la commune : "
    + ", ".join(_bouts) + ". Appelez le 07 61 08 36 08."
)
IMG_EXT = (".webp", ".png", ".jpg", ".jpeg", ".svg", ".gif")
# The address that answers: it is the one on the legal pages.
EMAIL = "carpentraspizzanapoli@gmail.com"
# Consent Mode v2, denied by default: no analytics cookie and no advertising
# identifier is set until the visitor accepts. Required in France (CNIL).
GA4 = (
    "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}\n"
    "var _c=null;try{_c=localStorage.getItem('consent-analytics');}catch(e){}\n"
    "gtag('consent','default',{'analytics_storage':_c==='1'?'granted':'denied',"
    "'ad_storage':'denied','ad_user_data':'denied','ad_personalization':'denied'});\n"
    "gtag('js',new Date());gtag('config','G-T2QW447J8J',{'anonymize_ip':true});</script>\n"
    '<script async src="https://www.googletagmanager.com/gtag/js?id=G-T2QW447J8J"></script>')

BANDEAU = '''<div id="consent-banner" role="dialog" aria-live="polite" aria-label="Consentement aux cookies de mesure" style="position:fixed;inset:auto 0 0 0;z-index:9999;background:#3D3328;color:#FFFDF7;padding:1rem 1.2rem;display:none;flex-wrap:wrap;gap:.8rem;align-items:center;justify-content:center;font-size:.85rem;line-height:1.5;">
<p style="margin:0;max-width:42rem;color:#FFFDF7;">Nous utilisons une mesure d'audience anonyme pour améliorer le site. Aucun cookie n'est déposé sans votre accord. <a href="/politique-de-confidentialite/" style="color:#C8972A;">En savoir plus</a></p>
<span style="display:flex;gap:.6rem;">
<button type="button" id="consent-no" style="padding:.5rem 1.1rem;border:1px solid rgba(255,253,247,.5);background:transparent;color:inherit;border-radius:2px;cursor:pointer;font:inherit;">Refuser</button>
<button type="button" id="consent-yes" style="padding:.5rem 1.1rem;border:none;background:#C8972A;color:#3D3328;border-radius:2px;cursor:pointer;font:inherit;font-weight:600;">Accepter</button>
</span></div>
<script>(function(){var b=document.getElementById('consent-banner');if(!b)return;
var s=null;try{s=localStorage.getItem('consent-analytics');}catch(e){}
/* display is set inline, so an [hidden] attribute would be overridden. */
if(s===null){b.style.display='flex';}
function rep(v){try{localStorage.setItem('consent-analytics',v);}catch(e){}
if(window.gtag)gtag('consent','update',{'analytics_storage':v==='1'?'granted':'denied'});b.style.display='none';}
document.getElementById('consent-yes').addEventListener('click',function(){rep('1');});
document.getElementById('consent-no').addEventListener('click',function(){rep('0');});})();</script>'''

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
    r'\bA lire aussi\b': "À lire aussi", r'\bA emporter\b': "À emporter",
    r'\bA partir de\b': "À partir de", r'\bA propos\b': "À propos",
}

# Words the site publishes without accents, resolved against a French
# dictionary: a word is listed only when it is NOT valid French as written and
# exactly one accented form exists. "ou", "a", "cote", "sur" are valid words,
# so they are absent — restoring those needs a human, not a table. Built by
# .github/scripts/construire_accents.py; the hand-checked list above wins.
_table = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "accents.json")
if os.path.exists(_table):
    ACCENTS = {**json.load(open(_table, encoding="utf-8")), **ACCENTS}

# One alternation instead of one pass per word: 600 regexes over every text
# node of 50 pages is a minute of CI time for nothing.
MOTIF_ACCENTS = re.compile(r'\b(' + "|".join(sorted(ACCENTS, key=len, reverse=True)) + r')\b',
                           re.IGNORECASE)

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
# Prices and recipes come from the printed flyer (carte.json), not from the
# page the guard is about to rewrite: reading the page would make every
# correction lag one run behind.
MENU = {n.lower(): (d["petite"], d["grande"]) for n, d in CARTE["pizzas"].items()}
MIN_PRICE = min(p for p26, p30 in MENU.values() for p in (p26,) if p)
# Cheapest large, counting only items sold in both sizes: the desserts are
# large-only and start at 3.50, which is not a pizza price.
MIN_PRICE_30 = min(p30 for p26, p30 in MENU.values() if p26 and p30)


def euro(p):
    return f"{int(p)}€" if abs(p - int(p)) < 0.005 else f"{int(p)}€{round((p - int(p)) * 100):02d}"


def sans_accent(nom):
    """Match menu names across apostrophes, accents and hyphens."""
    base = unicodedata.normalize("NFKD", nom.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", base).strip()


CARTE_PAR_CLE = {sans_accent(n): (n, d) for n, d in CARTE["pizzas"].items()}


def remplacer_div(c, ident, neuf):
    """Replace a whole <div id="…">…</div>, counting nesting rather than
    guessing at a closing pattern: a regex that assumes how many </div> sit at
    the end silently does nothing the day the markup gains a paragraph."""
    depart = c.find(f'<div id="{ident}"')
    if depart == -1:
        return c, False
    profondeur, i = 0, depart
    for m in re.finditer(r'<div\b|</div>', c[depart:]):
        profondeur += 1 if m.group(0) == "<div" else -1
        if profondeur == 0:
            i = depart + m.end()
            break
    else:
        return c, False
    return c[:depart] + neuf + c[i:], True


FAVICONS = "\n".join(
    t for t in re.findall(r'<link[^>]*rel="(?:shortcut )?(?:icon|apple-touch-icon)"[^>]*>', home_html)
    if (lambda h: h and os.path.exists(os.path.join(SITE, h.group(1).lstrip("/"))))(
        re.search(r'href="([^"]+)"', t)))

print(f"Source of truth: {RATING}/5 — {COUNT} avis · {len(MENU)} pizzas, dès {euro(MIN_PRICE)}\n")

# ---------- médias fournis par la pizzeria ----------
# Le guard travaille sur un clone de la production, où ces fichiers n'existent
# pas encore : ils sont versionnés ici et déposés dans le site au passage.
MEDIAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "medias")
for _src in sorted(glob.glob(os.path.join(MEDIAS, "*"))):
    _dst = os.path.join(SITE, os.path.basename(_src))
    if not os.path.exists(_dst) or os.path.getsize(_dst) != os.path.getsize(_src):
        shutil.copy2(_src, _dst)
        log(os.path.basename(_src), "média déposé dans le site")

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
    c = re.sub(r'\b[1-5][,.]\d★', f'{RATING_COMMA}★', c)
    # The number and its "/5" can be split by markup: 4,2<span>/5</span>.
    c = re.sub(r'\b[1-5],\d(?=(?:<[^>]+>)+\s*/\s*5)', RATING_COMMA, c)
    # Animated counters ship their final value, so a crawler or a reader
    # without JavaScript sees 526 rather than "0 Avis Google".
    c = re.sub(r'(data-target="(\d+)"[^>]*>)0(</span>)', r'\1\2\3', c)
    c = re.sub(r'(id="ratingCounter"[^>]*>)0(<)', rf'\g<1>{RATING_COMMA}\2', c)
    c = re.sub(r'(id="yearsCounter"[^>]*>)0(<)',
               rf'\g<1>{date.today().year - int(FOUNDED)}\2', c)
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
    # The second alternative is this rule's own output: anchored only on the
    # original wording, it stopped enforcing the moment it had fired once, and
    # the answer froze with the minimums of the day.
    c = re.sub(
        r'(?:dès 2 grandes pizzas commandées sur Carpentras et communes environnantes'
        r'|sur Carpentras et les communes environnantes)'
        r'[^"<]*?Appelez le 07 61 08 36 08\.',
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

        # Au-delà de 60 caractères Google coupe, et c'est la marque en fin de
        # titre qui disparaît. On retire d'abord les segments de queue, puis
        # les tournures décoratives, et on remet une marque courte s'il reste
        # de la place. Aucun mot-clé de recherche n'est retiré.
        if len(unescape(t)) > 60:
            bouts = [x for x in re.split(r'\s*[|—]\s*', t) if x.strip()]
            while len(bouts) > 1 and len(unescape(" | ".join(bouts))) > 60:
                bouts.pop()
            t = " | ".join(bouts)
            if len(unescape(t)) > 60:
                for deco in (" ? Sorties, Patrimoine + Pizza", " ? Sorties &amp; Pizza",
                             " ? Marchés, Sorties &amp; Pizza", " ? Sorties, Patrimoine &amp; Pizza",
                             " — Toutes Vos Questions", " — Guide Pratique",
                             " : Pourquoi Ça Change Tout"):
                    if deco in t:
                        t = t.replace(deco, " ?" if deco.startswith(" ?") else "")
            # Titre d'un seul tenant : la partie après le deux-points est une
            # glose, le mot-clé est avant.
            if len(unescape(t)) > 60 and " : " in t:
                t = t.split(" : ")[0].strip()
            if "Pizza Napoli" not in t and len(unescape(t)) + 15 <= 60:
                t += " | Pizza Napoli"
            t = re.sub(r'\s{2,}', ' ', t).strip(" |—-")

        # Measure what the reader sees: &amp; is one character, not five.
        shown, was = len(unescape(t)), len(unescape(old))
        if t != old and shown <= 65:
            log(rel, f"title {was} -> {shown} car.")
            return f"<title>{t}</title>"
        return m.group(0)

    c = re.sub(r'<title>([^<]*)</title>', trim_title, c)

    # Une description de plus de 165 caractères est coupée dans les résultats,
    # et c'est la fin — souvent l'appel à l'action — qui saute. On coupe sur
    # une frontière de phrase ou de mot, jamais au milieu.
    def trim_desc(m):
        avant, d = m.group(1), unescape(m.group(2))
        if len(d) <= 165:
            return m.group(0)
        coupe = d[:158]
        point = max(coupe.rfind(". "), coupe.rfind(" · "), coupe.rfind(" — "))
        d2 = (coupe[:point + 1] if point > 90 else coupe[:coupe.rfind(" ")] + "…").strip()
        log(rel, f"meta description {len(d)} -> {len(d2)} car.")
        return f'{avant}{d2}"'

    c = re.sub(r'(<meta name="description" content=")([^"]*)"', trim_desc, c)

    # Pizzas must be named as the menu names them: "Margharita" appeared 18
    # times against 10 correct spellings, including in a title. This runs
    # before the price rules because they look prices up by name.
    c = c.replace("Margharita", "Margherita")

    # 6e. prices quoted in prose must match the menu. The negative lookbehind
    # matters: an earlier version rewrote "grande dès 12€50" to "dès 7€90" as
    # well, advertising every large pizza at the small-size price.
    # `\s*\d{0,2}` used to swallow the space before the next word whenever the
    # price had no cents, so "dès 7€ la petite" lost its space on the next run.
    c = re.sub(r'(?<!petite )(?<!grande )dès\s*\d+\s*€(?:\s*\d{2})?', f'dès {euro(MIN_PRICE)}', c)
    c = re.sub(r'[Pp]izzas? dès \d+\s*€\s*\d{0,2}', f'Pizzas dès {euro(MIN_PRICE)}', c)

    # Price badges on the "best pizzas" list, derived from the menu by name.
    noms = re.findall(r'class="pizza-name"[^>]*>([^<]+)<', c)
    if noms and 'class="pizza-price-badge"' in c:
        file_noms = iter(noms)

        def badge(m):
            nom = next(file_noms, "")
            cle = re.sub(r"^(La|Le|Les|L')\s*", "", nom.strip(), flags=re.I).lower()
            p26, p30 = MENU.get(cle, (None, None))
            if p30 is None:
                return m.group(0)
            neuf = (f'petite dès {euro(p26)}<br>grande dès {euro(p30)}' if p26
                    else f'grande dès {euro(p30)}')
            if neuf != m.group(1):
                log(rel, f"prix {nom} : {re.sub('<br>', ' / ', m.group(1))} -> {neuf.replace('<br>', ' / ')}")
            return m.group(0).replace(m.group(1), neuf)

        c = re.sub(r'class="pizza-price-badge"[^>]*>(.*?)</div>', badge, c, flags=re.DOTALL)

    # Prose that quotes a starting price for both sizes, markup included.
    c = re.sub(r'démarrent à\s*(<strong>)?\d+\s*€\s*\d{0,2}(</strong>)?\s*en petite et\s*'
               r'(<strong>)?\d+\s*€\s*\d{0,2}(</strong>)?\s*en grande',
               f'démarrent à <strong>{euro(MIN_PRICE)}</strong> en petite et '
               f'<strong>{euro(MIN_PRICE_30)}</strong> en grande', c)

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

    # La bannière reprend la charte du dépliant, choisie par la pizzeria : la
    # photo reste entièrement vive, et le texte vit dans un panneau noir bordé
    # d'or, comme les encadrés d'information au dos du dépliant. Le nom est
    # composé comme sur le papier — P vert, N rouge, filet drapeau — et le
    # numéro en Bebas Neue, la police du dépliant.
    # Les classes d'origine sont conservées : le script qui change le libellé
    # du bouton à 17h30 et les tests s'y accrochent.
    c = c.replace("hero1.webp", "hero-mozza.webp").replace("hero1.jpg", "hero-mozza.jpg")
    for _ancien in ("linear-gradient(to bottom,rgba(0,0,0,.50) 0%,rgba(0,0,0,.15) 40%,rgba(0,0,0,.60) 100%)",
                    "linear-gradient(to bottom,rgba(0,0,0,.58) 0%,rgba(0,0,0,.44) 40%,rgba(0,0,0,.66) 100%)",
                    "radial-gradient(ellipse 58% 48% at 50% 48%,rgba(0,0,0,.72) 0%,"
                    "rgba(0,0,0,.5) 55%,rgba(0,0,0,.12) 82%,rgba(0,0,0,.05) 100%)"):
        c = c.replace(_ancien, "linear-gradient(rgba(27,23,20,.22),rgba(27,23,20,.22))")
    c = c.replace(".hero::before{content:'';position:absolute;inset:0;"
                  "background:radial-gradient(ellipse at center,transparent 30%,rgba(0,0,0,.35) 100%);}",
                  ".hero::before{content:'';position:absolute;inset:0;"
                  "background:radial-gradient(ellipse at center,transparent 62%,rgba(0,0,0,.10) 100%);}")

    if rel == "index.html" and "hero-panneau" not in c and '<section class="hero">' in c:
        c = c.replace(
            "family=Cinzel:wght@400;600;700;900&family=Josefin+Sans:wght@300;400;600;700",
            "family=Cinzel:wght@400;600;700;900&family=Josefin+Sans:wght@300;400;600;700"
            "&family=Playfair+Display:wght@700;900&family=Bebas+Neue&family=Manrope:wght@200;300;600", 1)
        _i = c.find('<section class="hero">')
        _j = c.find("</section>", _i)
        _scroll = '<div class="hero-scroll"><div class="scroll-line"></div>Découvrir</div>'
        c = c[:_i] + (
            '<section class="hero"> <div class="hero-panneau">'
            ' <div class="hero-badge">Pizzeria artisanale · Depuis 2008</div>'
            ' <h1><span class="mv">P</span>izza <span class="mr">N</span>apoli<em>Carpentras</em></h1>'
            ' <div class="hero-drapeau"><span></span><span></span><span></span></div>'
            ' <p class="hero-sub">Pâte maison, ingrédients sélectionnés chaque jour.</p>'
            ' <p class="hero-tel-label">Commandez au</p>'
            ' <p class="hero-tel">07 61 08 36 08</p>'
            ' <div class="hero-btns">'
            ' <a href="#" onclick="openCommander();return false;" class="btn-primary btn-commander-online">🍕 Commander</a>'
            ' <a href="#menu" class="btn-outline">Voir le menu</a>'
            ' </div> </div> ' + _scroll + '\n'
        ) + c[_j:]
        c = c.replace("</head>",
            "<style>\n"
            ".hero-panneau{position:relative;z-index:3;background:rgba(27,23,20,.90);"
            "border:1px solid #8C6E2E;border-radius:3px;padding:3rem 3.4rem 2.8rem;"
            "max-width:720px;margin:0 1.2rem;box-shadow:0 30px 70px rgba(0,0,0,.5);"
            "display:flex;flex-direction:column;align-items:center;text-align:center;}\n"
            ".hero .hero-badge{background:none;border:none;padding:0;color:#D9AB4C;"
            "text-shadow:none;font-family:'Manrope',sans-serif;font-size:.72rem;"
            "letter-spacing:.26em;margin-bottom:1.4rem;}\n"
            ".hero h1{font-family:'Playfair Display',serif;font-weight:900;color:#fff;"
            "font-size:clamp(2.4rem,6vw,4.1rem);line-height:.98;margin-bottom:0;text-shadow:none;}\n"
            ".hero h1 .mv{color:#1E7A3E;} .hero h1 .mr{color:#E2323A;}\n"
            ".hero h1 em{display:block;font-family:'Playfair Display',serif;font-style:italic;"
            "font-weight:700;color:#D9AB4C;font-size:.46em;margin-top:.18em;}\n"
            ".hero-drapeau{display:flex;width:150px;height:6px;margin:1.1rem 0 0;"
            "opacity:0;animation:fadeUp .8s ease forwards;animation-delay:1s;position:relative;z-index:2;}\n"
            ".hero-drapeau span{flex:1} .hero-drapeau span:nth-child(1){background:#1E7A3E}"
            ".hero-drapeau span:nth-child(2){background:#fff}"
            ".hero-drapeau span:nth-child(3){background:#E2323A}\n"
            ".hero .hero-sub{font-family:'Manrope',sans-serif;font-weight:200;color:#CDC6BB;"
            "font-size:clamp(.95rem,1.8vw,1.05rem);letter-spacing:.04em;margin:1.7rem 0 0;}\n"
            ".hero-tel-label{font-family:'Manrope',sans-serif;font-size:.68rem;letter-spacing:.3em;"
            "text-transform:uppercase;color:#D9AB4C;font-weight:600;margin-top:1.6rem;"
            "opacity:0;animation:fadeUp .9s ease forwards;animation-delay:1.05s;position:relative;z-index:2;}\n"
            ".hero-tel{font-family:'Bebas Neue',sans-serif;font-size:clamp(2.3rem,5.4vw,3.6rem);"
            "color:#fff;letter-spacing:.07em;line-height:1.05;margin:0;"
            "opacity:0;animation:fadeUp .9s ease forwards;animation-delay:1.1s;position:relative;z-index:2;}\n"
            ".hero .hero-btns{margin-top:1.8rem;}\n"
            ".hero .btn-outline{border-color:#D9AB4C;color:#D9AB4C;}\n"
            "@media(max-width:640px){.hero-panneau{padding:2rem 1.4rem 1.8rem;}}\n"
            "</style>\n</head>", 1)
        log(rel, "bannière reprise sur la charte du dépliant (panneau bordé d'or)")

    # L'écran d'intro au drapeau bloquait la page 2 secondes à chaque visite :
    # 1,2 s d'attente puis 0,8 s de fondu. Ramené à 0,7 s au total. Les textes
    # de la bannière étaient minutés pour apparaître après lui — les décaler
    # aussi, sinon la bannière reste vide une seconde et demie.
    c = c.replace("getElementById('loader').classList.add('hide'),1200)",
                  "getElementById('loader').classList.add('hide'),350)")
    c = c.replace("#loader{position:fixed;inset:0;display:flex;align-items:center;"
                  "justify-content:center;z-index:9999;transition:opacity .8s ease,visibility .8s;",
                  "#loader{position:fixed;inset:0;display:flex;align-items:center;"
                  "justify-content:center;z-index:9999;transition:opacity .35s ease,visibility .35s;")
    for _avant, _apres in (("animation-delay:1.8s", "animation-delay:.75s"),
                           ("animation-delay:2s", "animation-delay:.9s"),
                           ("animation-delay:2.2s", "animation-delay:1.05s"),
                           ("animation-delay:2.4s", "animation-delay:1.2s")):
        c = c.replace(_avant, _apres)

    # 6h. accents dropped by a generator that transliterated to ASCII.
    # Text nodes only: attributes carry file names and URLs, and accenting
    # img/chateau.webp into img/château.webp breaks the image.
    def accentuer(texte):
        def rendre(m):
            source = m.group(0)
            cible = ACCENTS.get(source.lower())
            if not cible:
                return source
            if source.isupper():
                return cible.upper()
            if source[0].isupper():
                return cible[0].upper() + cible[1:]
            return cible

        texte = MOTIF_ACCENTS.sub(rendre, texte)
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

    # The description Google prints is an attribute, so the walk above never
    # saw it: seven titles and every description stayed unaccented.
    def accentuer_attribut(m):
        return m.group(1) + accentuer(m.group(2)) + m.group(3)

    c = re.sub(r'(<meta[^>]*(?:name|property)="(?:description|og:description|twitter:description)"[^>]*content=")'
               r'([^"]*)(")', accentuer_attribut, c)
    c = re.sub(r'(<meta[^>]*content=")([^"]*)("[^>]*(?:name|property)="(?:description|og:description|twitter:description)")',
               accentuer_attribut, c)

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

    # Consent Mode v2 and the banner travel together: measurement without a
    # way to refuse it is not lawful here.
    if "googletagmanager" in c and "consent-banner" not in c and "</body>" in c:
        c = c.replace("</body>", BANDEAU + "\n</body>", 1)
        log(rel, "bandeau de consentement ajouté")
    # A page-level p{color:...} beats an inherited colour: on one page the
    # banner text came out at contrast 1.08, unreadable, which is not informed
    # consent. Pin the colour on the paragraph itself.
    if 'id="consent-banner"' in c and 'max-width:42rem;color:' not in c:
        c = c.replace('<p style="margin:0;max-width:42rem;">',
                      '<p style="margin:0;max-width:42rem;color:#FFFDF7;">')
        log(rel, "couleur du bandeau forcée sur le paragraphe")
    if "gtag('consent','default'" not in c and "googletagmanager" in c:
        c = re.sub(r"gtag\('js',new Date\(\)\);",
                   "gtag('consent','default',{'analytics_storage':(function(){try{return "
                   "localStorage.getItem('consent-analytics')==='1'?'granted':'denied';}"
                   "catch(e){return 'denied';}})(),'ad_storage':'denied','ad_user_data':'denied',"
                   "'ad_personalization':'denied'});gtag('js',new Date());", c, count=1)
        log(rel, "Consent Mode v2 (refus par défaut)")

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

    # 6m. the <main> target existed but no link ever pointed at it.
    # The anchor used to be </nav>, but on the homepage that </nav> sits inside
    # <div id="header-wrap">, whose </div> follows immediately: the parser closed
    # <main> straight away and the entire page ended up outside the landmark.
    # Slide the opening tag past any closing tags that directly follow it.
    m_ouvre = re.search(r'<main\b[^>]*>((?:\s*</\w+>)+)', c)
    if m_ouvre:
        balise = re.match(r'<main\b[^>]*>', m_ouvre.group(0)).group(0)
        c = c.replace(m_ouvre.group(0), m_ouvre.group(1) + balise, 1)
        log(rel, "<main> déplacé hors de l'en-tête (landmark vide)")

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
    lcp_deja_declare = bool(re.search(r'<link[^>]+rel="preload"[^>]+as="image"', c))
    # An existing high-priority image must not be left behind either.
    if lcp_deja_declare:
        c = re.sub(r'(<img[^>]*?) loading="eager" fetchpriority="high"', r'\1 loading="lazy"', c)

    def dimensionner(m):
        tag, src = m.group(0), re.search(r'src="([^"]+)"', m.group(0))
        if not src:
            return tag
        if "width=" not in tag or "height=" not in tag:
            taille = mesurer(src.group(1), base_dir)
            if taille:
                tag = tag[:-1].rstrip() + f' width="{taille[0]}" height="{taille[1]}">'
        # Only promote the first image when nothing else already claims the
        # LCP. The homepage preloads a CSS background hero, so promoting an
        # <img> further down put two files in a priority race.
        if premiere[0]:
            premiere[0] = False
            if not lcp_deja_declare:
                tag = tag.replace(' loading="lazy"', ' loading="eager" fetchpriority="high"')
        return tag

    avant_img = c
    c = re.sub(r'<img\s[^>]*>', dimensionner, c)
    if c != avant_img:
        log(rel, "dimensions d'images / priorité LCP")

    # 6p2. image names quoted in JavaScript escape the <img> rules above, and
    # GitHub Pages is case-sensitive: 'orientale.jpg' never matched
    # Orientale.jpg, so that pizza had no photo in the order form.
    def caser(m):
        ref = m.group(2)
        if exists_local(ref, base_dir) or "/" in ref:
            return m.group(0)
        for nom in os.listdir(base_dir or "."):
            if nom.lower() == ref.lower() and nom != ref:
                log(rel, f"casse du fichier : {ref} -> {nom}")
                return m.group(0).replace(ref, nom)
        return m.group(0)

    c = re.sub(r"(['\"])([\w.\-]+\.(?:jpg|jpeg|png|webp))\1", caser, c)

    # 6p3. favicon: declared on 5 pages of 46, and two of the three files did
    # not exist. Drop the dead declarations, carry the surviving ones everywhere.
    def lien_mort(m):
        href = re.search(r'href="([^"]+)"', m.group(0))
        if href and not exists_local(href.group(1), SITE):
            log(rel, f"déclaration d'icône morte retirée : {href.group(1)}")
            return ""
        return m.group(0)

    c = re.sub(r'<link[^>]*rel="(?:shortcut )?(?:icon|apple-touch-icon)"[^>]*>', lien_mort, c)
    if FAVICONS and "rel=\"icon\"" not in c and "</head>" in c:
        c = c.replace("</head>", FAVICONS + "\n</head>", 1)
        log(rel, "favicon déclaré")

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

    # 6t. the nine delivery pages were 96% identical once the town name was
    # neutralised — a doorway-page profile. What genuinely differs is the
    # minimum order, and stating it here also answers the customer before they
    # compose a basket the form would refuse at the last step.
    if seg and seg.startswith("livraison-pizza-") and "zone-minimum" not in c:
        ville = seg[len("livraison-pizza-"):]
        if ville in COMMUNES:
            nom, cp, mini, guide = COMMUNES[ville]
            liens = []
            if os.path.exists(os.path.join(SITE, "blog", f"guide-{guide}.html")):
                liens.append(f'<a href="{HOST}/blog/guide-{guide}.html">notre guide de {nom}</a>')
            if os.path.exists(os.path.join(SITE, "blog", f"que-faire-{ville}-ce-soir", "index.html")):
                liens.append(f'<a href="{HOST}/blog/que-faire-{ville}-ce-soir/">que faire à {nom} ce soir</a>')
            bloc = (
                f'<div class="zone-minimum" style="margin:2rem auto;max-width:640px;padding:1.2rem 1.4rem;'
                f'background:#FFFDF7;border-left:4px solid #C8972A;border-radius:2px;">'
                f'<h2 style="margin:0 0 .6rem;font-size:1.05rem;">Livraison à {nom} ({cp})</h2>'
                f'<p style="margin:0 0 .5rem;"><strong>Minimum de commande : {mini} grandes pizzas '
                f'(ou {mini * 2} petites).</strong> La livraison est gratuite dès ce minimum atteint, '
                f'tous les soirs de 19h00 à 22h00. Les commandes sont prises dès 17h30 au '
                f'<a href="tel:0761083608">07 61 08 36 08</a>.</p>'
                + (f'<p style="margin:0;">Pour préparer votre soirée : {" et ".join(liens)}.</p>' if liens else "")
                + '</div>')
            if "</main>" in c:
                c = c.replace("</main>", bloc + "\n</main>", 1)
            elif "<footer" in c:
                c = c.replace("<footer", bloc + "\n<footer", 1)
            log(rel, f"minimum de commande annoncé ({mini} grandes)")

    # 6t2. The minimum is written out in three shapes across the site, and all
    # three carry the town name, so COMMUNES can correct them wherever they
    # sit: the block above, the prose on the guides, and the zone table.
    if seg and seg.startswith("livraison-pizza-") and seg[len("livraison-pizza-"):] in COMMUNES:
        _mini = COMMUNES[seg[len("livraison-pizza-"):]][2]
        c = re.sub(r'Minimum de commande : \d+ grandes pizzas \(ou \d+ petites\)',
                   f'Minimum de commande : {_mini} grandes pizzas (ou {_mini * 2} petites)', c)

    NOM_VERS_MIN = {sans_accent(n): m for n, _cp, m, _g in COMMUNES.values()}
    NOM_VERS_MIN.update({cp: m for _n, cp, m, _g in COMMUNES.values()})

    def _prose(m):
        mini = NOM_VERS_MIN.get(sans_accent(m.group("ou")))
        fort = "<strong>" if m.group("o") else ""
        return m.group(0) if mini is None else (
            f'minimum est de {fort}{mini} grandes pizzas{"</strong>" if fort else ""} '
            f'pour une livraison {m.group("prep")} {m.group("ou")}')

    c = re.sub(r'minimum est de (?P<o><strong>)?\d+ grandes pizzas(?:</strong>)? '
               r'pour une livraison (?P<prep>à|en) (?P<ou>[^.<]+)', _prose, c)

    def _tableau(m):
        secteur = (m.group("sect") or "").strip().lower()
        cle = sans_accent(m.group("ville"))
        mini = SECTEURS.get((cle, secteur)) or NOM_VERS_MIN.get(cle)
        return m.group(0) if mini is None else (
            f'{m.group("tete")}{mini} grandes (ou {mini * 2} petites)')

    c = re.sub(r'(?P<tete>📍\s*(?P<ville>[^<]+?)\s*(?:<span[^>]*>\((?P<sect>[^)]*)\)</span>\s*)?'
               r'</td>\s*<td[^>]*>)\d+ grandes \(ou \d+ petites\)', _tableau, c)

    _bornes = sorted({m for _n, _cp, m, _g in COMMUNES.values()
                      if m != COMMUNES["carpentras"][2]})
    c = re.sub(r'autres communes dès [\d,\s]*(?:ou|et)\s*\d+',
               "autres communes dès " + ", ".join(str(b) for b in _bornes[:-1])
               + f" ou {_bornes[-1]}", c)

    # 6t4. Le minimum est écrit d'au moins six façons : tableau « N grandes
    # (ou M petites) », tableau « N grandes pizzas », « dessert VILLE — N
    # grandes », « Minimum N grandes », la meta description, l'og:description.
    # Une règle par forme, c'est une forme oubliée à chaque fois — Pernes est
    # resté à 3 pendant que tout le reste passait à 5. On apparie donc le
    # nombre à la commune la plus proche qui le précède, quel que soit le
    # balisage entre les deux.
    MINI = {n: m for n, _cp, m, _g in COMMUNES.values()}
    _villes = sorted(MINI, key=len, reverse=True)
    _re_ville = re.compile("|".join(re.escape(v) for v in _villes))
    _re_nombre = re.compile(r'(\d+)(\s*)(grandes?|petites?)\b')
    _marque = re.compile(r'(Pizza )?Napoli\s*$|pizzanapoli', re.IGNORECASE)
    _commune_page = COMMUNES.get(seg[len("livraison-pizza-"):], (None,))[0] \
        if seg and seg.startswith("livraison-pizza-") else None

    def _accorder(texte):
        villes = [(m.end(), m.group(0)) for m in _re_ville.finditer(texte)]
        sortie, dernier, change = [], 0, 0
        for m in _re_nombre.finditer(texte):
            avant = [v for v in villes if v[0] <= m.start()]
            ville, ecart = (avant[-1][1], m.start() - avant[-1][0]) if avant else (None, 10 ** 9)
            # Une commune cachée dans « Pizza Napoli Carpentras » ne compte pas.
            if ville and _marque.search(texte[max(0, avant[-1][0] - len(ville) - 14):avant[-1][0] - len(ville)]):
                ville, ecart = None, 10 ** 9
            # Trop loin, ou séparé par une autre ligne : la page tranche.
            if ecart > 90 or re.search(r'</tr>|</li>|</ul>|📍', texte[m.start() - ecart:m.start()]):
                ville = _commune_page
            if ville not in MINI:
                continue
            attendu = MINI[ville] * (2 if m.group(3).startswith("petite") else 1)
            if int(m.group(1)) != attendu:
                sortie.append(texte[dernier:m.start()] + f"{attendu}{m.group(2)}{m.group(3)}")
                dernier = m.end()
                change += 1
        return ("".join(sortie) + texte[dernier:], change) if change else (texte, 0)

    if _commune_page or (seg and seg in ("livraison-pizza-84200",)) or rel == "index.html":
        c, _n = _accorder(c)
        if _n:
            log(rel, f"{_n} minimum(s) de commande réaccordé(s) sur la commune citée")

    # 6u. Sarrians. Four pages told four different stories; the arbiter is the
    # order form, and getMinPizzasForCity() does not list Sarrians, so an order
    # there is refused. The pages that promised delivery were the wrong ones.
    if "Sarrians" in c:
        c = re.sub(
            r'<div class="conseil-box">\s*<h3>Pizza Napoli livre à Sarrians[^<]*</h3>\s*<ul>\s*'
            r'<li><strong>Livraison à Sarrians\s*:</strong>[^<]*</li>',
            '<div class="conseil-box">\n      <h3>Commander depuis Sarrians</h3>\n      <ul>\n'
            '        <li><strong>Livraison :</strong> Sarrians n\'est pas dans notre zone de '
            'livraison. La commande reste possible à emporter.</li>', c)
        c = c.replace("Que faire à Sarrians ce soir ? Idées + pizza livrée.",
                      "Que faire à Sarrians ce soir ? Nos idées de sorties.")
        c = c.replace("Livraison pizza à Sarrians", "Pizza à emporter depuis Sarrians")
        c = re.sub(r'(communes voisines\s*:[^<.]*?),\s*Sarrians', r'\1', c)
        if "livre à Sarrians" not in c and "🛵 Sarrians" in c:
            c = c.replace("🛵 Sarrians", "")
            log(rel, "Sarrians : mentions de livraison retirées (commune non desservie)")

    # 6v. the order form could only be opened from the homepage, while the 37
    # other pages are the ones that catch search traffic. They now link to
    # /#commander, and the homepage opens the form when it sees that hash.
    if rel == "index.html" and "commanderDepuisHash" not in c:
        c = c.replace("</body>",
                      "<script>function commanderDepuisHash(){if(location.hash==='#commander'"
                      "&&typeof openCommander==='function'){openCommander();}}"
                      "window.addEventListener('hashchange',commanderDepuisHash);"
                      "window.addEventListener('load',commanderDepuisHash);</script>\n</body>", 1)
        log(rel, "ouverture du formulaire par #commander")

    # 6w. the form promises a recap by email while asking for no email address.
    c = re.sub(r'Un r[ée]capitulatif de votre commande vous sera envoy[ée] par email[^<.]*\.',
               "Votre commande est transmise à notre équipe, qui vous rappelle pour la confirmer.", c)

    # 6x. the privacy policy said data never reaches a third party, while the
    # order is sent through WhatsApp — that is a transfer to Meta.
    # The trailing lookahead is what stops the rule appending its own sentence
    # a second time: the document-wide check passes as long as one page has it.
    if "Meta Platforms Ireland" not in c:
        c = re.sub(
            r'(jamais vendues ni transmises[^.]*?)(,\s*sauf obligation l[ée]gale\.)'
            r'(?!\s*Les informations de votre commande)',
            r'\1\2 Les informations de votre commande (nom, téléphone, adresse de livraison) '
            r'transitent par WhatsApp — Meta Platforms Ireland Ltd — pour être transmises à notre '
            r'équipe, et par notre prestataire d’envoi de formulaire.', c)

    # 6y. Order notifications were landing in Gmail's spam folder. Web3Forms
    # always sends from its own domain — there is no way to align SPF/DKIM with
    # ours — so the mail cannot be made to look like it comes from us. What we
    # can do is give the message a stable, ASCII, unambiguous identity: a fixed
    # subject prefix the inbox can filter on without depending on the sender
    # address, a sender name instead of the default "Notifications", and a
    # reply-to that points back at the pizzeria.
    if "api.web3forms.com/submit" in c:
        avant = c
        c = re.sub(r"subject:\s*'[^']*'\s*\+\s*fullNom",
                   "subject:'COMMANDE SITE - '+fullNom", c)
        c = re.sub(r"(access_key:\s*'[0-9a-f-]+',)(?!\s*from_name)",
                   r"\1\nfrom_name:'Commandes Pizza Napoli',\n"
                   f"replyto:'{EMAIL}',", c)
        if c != avant:
            log(rel, "notification de commande : objet filtrable, expéditeur nommé")

    # 6z. The order form's menu is aligned on the printed flyer: a recipe that
    # reads differently on paper and on screen is a complaint waiting to be
    # made. Names, ingredients and prices all come from carte.json. Entries are
    # corrected in place; one that exists on only one side is reported, never
    # added or deleted by a regular expression.
    if "const PIZZAS" in c:
        for ancien, neuf in CARTE["renommages"].items():
            if f"name:'{ancien}'" in c:
                c = c.replace(f"name:'{ancien}'", f"name:'{neuf}'")
                log(rel, f"carte : « {ancien} » renommée « {neuf} » (nom du dépliant)")

        vus, corriges = set(), [0]

        def _aligner(m):
            nom = m.group("nom1") or m.group("nom2")
            cle = sans_accent(nom)
            vus.add(cle)
            if cle not in CARTE_PAR_CLE:
                return m.group(0)
            _, ref = CARTE_PAR_CLE[cle]
            bout = m.group(0)
            if "'" not in ref["ingredients"]:
                bout = re.sub(r"ingr:'[^']*'", "ingr:'" + ref["ingredients"] + "'", bout)
            for champ, prix in (("p26", ref["petite"]), ("p30", ref["grande"])):
                val = "null" if prix is None else f"{prix:.2f}"
                bout = re.sub(rf"{champ}:(?:[\d.]+|null)", f"{champ}:{val}", bout)
            if bout != m.group(0):
                corriges[0] += 1
            return bout

        motif = (r"\{cat:'[^']*',\s*name:(?:'(?P<nom1>[^']*)'|\"(?P<nom2>[^\"]*)\"),"
                 r"\s*ingr:'[^']*',\s*p26:(?:[\d.]+|null),\s*p30:(?:[\d.]+|null)\}")
        c = re.sub(motif, _aligner, c)
        if corriges[0]:
            log(rel, f"carte alignée sur le dépliant ({corriges[0]} recette(s) corrigée(s))")
        manquantes = [CARTE_PAR_CLE[k][0] for k in CARTE_PAR_CLE if k not in vus]
        if manquantes:
            log(rel, f"ALERTE recettes du dépliant absentes du formulaire : {', '.join(manquantes)}")
        hors = [k for k in vus if k not in CARTE_PAR_CLE
                and k not in {sans_accent(n) for n in CARTE["hors_depliant_conservees"]}]
        if hors:
            log(rel, f"ALERTE recettes du formulaire absentes du dépliant : {', '.join(hors)}")

    # 6z2. The delivery rule was written out three times: this table,
    # getMinPizzasForCity(), and a third copy inlined in envoyerWhatsApp() —
    # and it is that third copy, not the named function, that actually decides
    # whether an order goes through. They had drifted. All of them are now
    # generated from COMMUNES, so they cannot. Names are tested before
    # postcodes because 84210 covers both Pernes-les-Fontaines and
    # Saint-Didier, and 84200 both Carpentras and Serres.
    ALIAS = {"saint-didier": ("saint-didier", "st-didier", "st didier"),
             "pernes-les-fontaines": ("pernes",),
             "loriol-du-comtat": ("loriol",)}
    PAR_CP = {}
    for _slug, (_nom, _cp, _mini, _g) in COMMUNES.items():
        PAR_CP.setdefault(_cp, set()).add(_mini)

    def _conditions(var):
        """One (condition, minimum) per line, strictest town first, postcodes last."""
        sortie = []
        for slug, (nom, cp, mini, _g) in sorted(COMMUNES.items(), key=lambda kv: -kv[1][2]):
            cond = " || ".join(f"{var}.indexOf('{m}') !== -1" for m in ALIAS.get(slug, (slug,)))
            if slug == "pernes-les-fontaines":     # Les Pennes-Mirabeau is 100 km away
                cond = f"({cond}) && {var}.indexOf('pennes') === -1"
            sortie.append((cond, mini))
        for cp, minis in sorted(PAR_CP.items(), key=lambda kv: -max(kv[1])):
            if len(minis) == 1:        # a postcode shared by two minimums decides nothing
                sortie.append((f"{var}.indexOf('{cp}') !== -1", next(iter(minis))))
        return sortie

    VILLES = ", ".join(n for n, _cp, _m, _g in COMMUNES.values())

    if "function getMinPizzasForCity" in c:
        corps = "\n".join(f"  if ({cond}) return {mini};" for cond, mini in _conditions("a"))
        neuve = ("function getMinPizzasForCity(addr) {\n  var a = addr.toLowerCase();\n"
                 + corps + "\n  return -1;\n}")
        avant = c
        c = re.sub(r"function getMinPizzasForCity\(addr\) \{.*?\n\}", neuve, c, flags=re.DOTALL)
        if c != avant:
            log(rel, "getMinPizzasForCity régénérée depuis COMMUNES")
        c = re.sub(r"Villes desservies : [^\\']*", f"Villes desservies : {VILLES}.", c)

    # The copy that actually gates the order, inside envoyerWhatsApp().
    if "/* === ZONE VALIDATION === */" in c:
        lignes = [f"    {'if' if i == 0 else 'else if'} ({cond}) _min = {mini};"
                  for i, (cond, mini) in enumerate(_conditions("_a"))]
        bloc = "var _min = -1;\n" + "\n".join(lignes) + "\n    if (_min === -1) {"
        avant = c
        c = re.sub(r"var _min = -1;.*?if \(_min === -1\) \{", bloc, c, flags=re.DOTALL)
        c = re.sub(r"Nous livrons uniquement a : [^\\']*", f"Nous livrons uniquement à : {VILLES}.", c)
        if c != avant:
            log(rel, "contrôle de zone de la commande régénéré depuis COMMUNES")

    # 6z3. The drinks list and the two offers come from the flyer. The old
    # popup knew only one tier, offered 1.5 L bottles the price list does not
    # contain, and counted a CSS class the form does not use — so it had never
    # once appeared. It is replaced wholesale by a panel generated from
    # carte.json: the highest tier the basket reaches is proposed, one offer per
    # order, and the chosen drink joins the order like any other line.
    if "const DRINKS" in c:
        lignes = ",\n".join(f"{{name:'{b['nom']}',price:{b['prix']:.2f}}}" for b in CARTE["boissons"])
        avant = c
        c = re.sub(r"const DRINKS = \[.*?\n\];", f"const DRINKS = [\n{lignes}\n];", c, flags=re.DOTALL)
        if c != avant:
            log(rel, f"boissons alignées sur le dépliant ({len(CARTE['boissons'])} références)")

    if "free-bottle-popup" in c or "offres-boisson" in c:
        offres = json.dumps(CARTE["offres"], ensure_ascii=False)
        evin = CARTE["mentions"]["alcool"]
        panneau = (
            '<div id="offres-boisson" style="display:none;position:fixed;inset:0;'
            'background:rgba(0,0,0,.7);z-index:10000;align-items:center;justify-content:center;">'
            '<div role="dialog" aria-labelledby="offre-titre" style="background:#FFFDF7;border-radius:12px;'
            'padding:1.6rem;max-width:400px;margin:1rem;max-height:86vh;overflow:auto;">'
            '<h3 id="offre-titre" style="color:#A8202A;font-size:1.15rem;margin:0 0 .4rem;">🎁 Votre offre</h3>'
            '<p id="offre-detail" style="color:#555;font-size:.9rem;margin:0 0 1rem;"></p>'
            '<div id="offre-choix" style="display:flex;flex-direction:column;gap:.5rem;"></div>'
            f'<p id="offre-evin" style="color:#777;font-size:.7rem;margin:.9rem 0 0;display:none;">{evin}</p>'
            '<p style="color:#999;font-size:.72rem;margin:.6rem 0 0;">Une offre par commande.</p>'
            '<button type="button" onclick="refuserOffre()" style="margin-top:.9rem;width:100%;'
            'padding:.6rem;border:1px solid #ccc;background:transparent;border-radius:8px;'
            'cursor:pointer;font:inherit;color:#555;">Non merci</button>'
            '</div></div>')
        script = (
            "<script>\n"
            f"var OFFRES = {offres};\n"
            "var offreChoisie = null, offreRefusee = false;\n"
            "function nbPizzas(){var n=0;Object.values(typeof pizzaOrders!=='undefined'?pizzaOrders:{})"
            ".forEach(function(o){n+=o.qty||0;});return n;}\n"
            "function offreApplicable(){var n=nbPizzas();"
            "for(var i=0;i<OFFRES.length;i++){if(n>=OFFRES[i].seuil)return OFFRES[i];}return null;}\n"
            "function proposerOffre(){var o=offreApplicable();"
            "if(!o||offreRefusee||(offreChoisie&&offreChoisie.seuil===o.seuil))return;\n"
            "document.getElementById('offre-detail').textContent=o.titre;\n"
            "document.getElementById('offre-evin').style.display=o.alcool?'block':'none';\n"
            "var z=document.getElementById('offre-choix');z.innerHTML='';\n"
            "o.choix.forEach(function(nom){var b=document.createElement('button');b.type='button';\n"
            "b.style.cssText='padding:.7rem;border:2px solid #A8202A;background:#fff;border-radius:8px;"
            "cursor:pointer;font:inherit;font-weight:600;';b.textContent=nom;\n"
            "b.onclick=function(){choisirOffre(nom,o);};z.appendChild(b);});\n"
            "document.getElementById('offres-boisson').style.display='flex';}\n"
            "function choisirOffre(nom,o){offreChoisie={nom:nom,prix:o.prix,seuil:o.seuil,titre:o.titre};\n"
            "document.getElementById('offres-boisson').style.display='none';\n"
            "if(typeof updateTotal==='function')updateTotal();}\n"
            "function refuserOffre(){offreRefusee=true;"
            "document.getElementById('offres-boisson').style.display='none';}\n"
            "function ligneOffre(){return offreChoisie?offreChoisie.nom+' ('+(offreChoisie.prix?"
            "euroFmt(offreChoisie.prix):'offert')+')':'';}\n"
            "var _nsOffre = typeof nextStep==='function'?nextStep:null;\n"
            "if(_nsOffre){nextStep=function(s){if(s===2){proposerOffre();}_nsOffre(s);};}\n"
            "</script>")
        avant = c
        # Remove the old popup, its handler and the nextStep override that drove it.
        c, remplace = remplacer_div(c, "free-bottle-popup", panneau)
        if not remplace:
            c, remplace = remplacer_div(c, "offres-boisson", panneau)
        if not remplace and "offres-boisson" not in c:
            log(rel, "ALERTE panneau d'offres introuvable, rien remplacé")
        c = re.sub(r"<script>\s*var selectedFreeBottle = '';.*?\n</script>", script, c, flags=re.DOTALL)
        c = re.sub(r"<script>\nvar OFFRES = .*?\n</script>", script, c, flags=re.DOTALL)
        if c != avant:
            log(rel, "offres boissons du dépliant : deux paliers (3 et 5 pizzas)")

    # The offer has to reach the total and the order message, or it is
    # decoration. Both run before the block that declares offreChoisie, so the
    # binding is tested rather than assumed.
    if "offreChoisie" in c and "function updateTotal" in c:
        if "offreRetenue" not in c:
            c = c.replace(
                "Object.values(drinkOrders).forEach(o=>{if(o.qty>0){total+=o.qty*o.price;count+=o.qty;}});",
                "Object.values(drinkOrders).forEach(o=>{if(o.qty>0){total+=o.qty*o.price;count+=o.qty;}});\n"
                "const offreRetenue = typeof offreChoisie!=='undefined' && offreChoisie;\n"
                "if(offreRetenue){total+=offreRetenue.prix;count++;}", 1)
        if "OFFRE :" not in c:
            c = c.replace(
                "msg+='💰 *Total estimé : '+euroFmt(total)+'*\\n';",
                "if(typeof offreChoisie!=='undefined' && offreChoisie){total+=offreChoisie.prix;"
                "msg+='🎁 *OFFRE :* '+ligneOffre()+'\\n\\n';}\n"
                "msg+='💰 *Total estimé : '+euroFmt(total)+'*\\n';", 1)
            log(rel, "offre reportée dans le total et le message de commande")

    # 6z4. The alerts a refused customer reads were written without accents, and
    # offered no way out. The flyer answers that case: "Hors zone ? Appelez-nous."
    c = c.replace("Desole, nous ne livrons pas a cette adresse.",
                  "Désolé, nous ne livrons pas à cette adresse.")
    c = c.replace("Verifiez votre adresse ou choisissez A emporter.",
                  "Vérifiez votre adresse ou choisissez À emporter.")
    c = re.sub(r"(Désolé, nous ne livrons pas à cette adresse\.\\n[^']*?)(?<!08\.)'",
               lambda m: m.group(1) + ("" if CARTE["mentions"]["hors_zone"] in m.group(1)
                                       else "\\n" + CARTE["mentions"]["hors_zone"]) + "'", c)
    c = c.replace("Minimum pour livrer a cette adresse :", "Minimum pour livrer à cette adresse :")
    c = c.replace("Votre commande equivaut a ", "Votre commande équivaut à ")
    c = c.replace("Ajoutez des pizzas pour commander en livraison.",
                  "Ajoutez des pizzas pour commander en livraison.")

    # 6z5. Two notices the flyer carries and the site did not spell correctly:
    # the allergen list (règlement INCO) and what the cheese is made of. The
    # homepage declared nine allergens and the CGV twelve; the longer list wins
    # everywhere, because under-declaring one cannot be taken back.
    avant = c
    c = re.sub(r'Allerg[eè]nes\s*:\s*nos pizzas peuvent contenir[^<]*',
               CARTE["mentions"]["allergenes"], c, flags=re.IGNORECASE)
    c = re.sub(r'La liste des allerg[eè]nes est disponible sur demande au 07 61 08 36 08\.\s*'
               r'Nos pizzas peuvent contenir\s*:[^<]*',
               CARTE["mentions"]["allergenes"], c, flags=re.IGNORECASE)
    c = re.sub(r'(<h[23][^>]*>\s*(?:\d+\.\s*)?)Allergenes(\s*</h[23]>)', r'\1Allergènes\2', c)
    if c != avant:
        log(rel, "mention allergènes harmonisée (liste complète, accentuée)")

    # 6z6. Batch from the September audit: statements that are simply wrong or
    # inconsistent, and that a rule can settle without inventing anything.

    # T3 — the blog announced delivery from 17h30, which is when orders open;
    # delivery starts at 19h. 28 pages repeated the same wrong line.
    c = re.sub(r"7j/7 de 17h30 [aà] 22h",
               "7j/7 · commande dès 17h30 · livraison 19h00–22h00", c)
    c = re.sub(r"livre 7 jours sur 7, du lundi au dimanche, de 17h30 [aà] 22h00\.",
               "prend les commandes 7 jours sur 7 dès 17h30 et livre de 19h00 à 22h00.", c)
    c = re.sub(r"La derni[èe]re commande est accept[ée]e [aà] 22h",
               "Le dernier créneau de livraison est 21h30", c)

    # E3 — "des 17h30" and "des 7€90" in the description Google displays. The
    # price rule runs earlier and only sees text nodes, so the attribute is
    # normalised here too rather than waiting a second run to settle.
    c = re.sub(r'\bdes (?=\d{1,2}h\d{2}\b|\d+\s*€)', "dès ", c)
    c = re.sub(r'(?<!petite )(?<!grande )dès\s*\d+\s*€(?:\s*\d{2})?', f'dès {euro(MIN_PRICE)}', c)

    # E5 — a grammar mistake used as an H2 on five articles.
    c = c.replace("Vous livrons aussi", "Nous livrons aussi")

    # E10 — the rim of a pizza is a bourrelet, or a cornicione. Not a rebourlet.
    c = re.sub(r'\brebourlet\b', "bourrelet", c, flags=re.IGNORECASE)

    # S11 — the street name, inside the JSON-LD too, which the text pass skips.
    c = c.replace("Pierre Semard", "Pierre Sémard")

    # T10 — "Plus de 80 recettes" is false whichever way the card is counted.
    c = c.replace("Plus de 80 recettes", "80 recettes")

    # T9 — one stray 4,2 next to twenty 4,5.
    c = re.sub(rf'\b4,2(?=\s*(?:&#9733;|★|/\s*5))', RATING.replace(".", ","), c)

    # T14 — "the cheapest" is a claim that has to be provable; the facts under
    # it are stronger anyway.
    c = c.replace("Quelle est la pizzeria la moins chère de Carpentras avec livraison à domicile ?",
                  "Combien coûte une pizza livrée à Carpentras ?")
    c = c.replace("C'est l'une des offres les plus accessibles de Carpentras et du Vaucluse",
                  "La livraison est gratuite dès le minimum de commande atteint")

    # T15 — "no hidden extras" sat next to a per-ingredient supplement and a
    # minimum order. Said straight, it is still an advantage.
    c = c.replace("Pas de frais de livraison, pas de suppléments cachés.",
                  "Livraison gratuite, sans frais de service ni majoration, "
                  "dès le minimum de commande de votre commune. "
                  "Ingrédient supplémentaire : 1,00 €.")

    # S5 — Serres is served, with the lowest minimum, and was missing from the
    # structured delivery area.
    if '"areaServed":[' in c and '{"@type":"City","name":"Serres"}' not in c:
        c = c.replace('"areaServed":[', '"areaServed":[{"@type":"City","name":"Serres"},', 1)
        log(rel, "Serres ajoutée à areaServed")

    # C6 — three Monteux rows for one commune, one an exact duplicate.
    if c.count("📍 Monteux") > 2:
        i = c.find("📍 Monteux</td>")
        if i != -1:
            debut = c.rfind("<tr", 0, i)
            fin = c.find("</tr>", i)
            if debut != -1 and fin != -1:
                c = c[:debut] + c[fin + len("</tr>"):]
                log(rel, "ligne Monteux en doublon retirée du tableau des zones")

    # T8 — the page telling the pizzeria's story contradicted the founding year
    # stated six times above it, and four different durations circulated.
    c = re.sub(r'\b20(?:10|09|11)\s*(—|–|-)\s*Ouverture', rf'{FOUNDED} \1 Ouverture', c)
    _ans = date.today().year - int(FOUNDED)
    c = re.sub(r'\b(?:1[0-9])\s*ans (d[\'’]expérience|d[\'’]artisanat|de savoir-faire|au cœur)',
               rf'{_ans} ans \1', c)
    c = re.sub(r'[Pp]lus de 1[0-9] ans', f"plus de {_ans} ans", c)

    # T11 — articles described pizzas that do not exist, or listed the wrong
    # toppings. The card is the reference, so the parenthesis is rewritten from
    # it. A pizza the card does not have is renamed to the one it meant.
    c = c.replace("la Spéciale Pizza Napoli", "la Napoli").replace("la 4 Fromages", "la 4 Fro")

    INGREDIENTS = {sans_accent(x) for d in CARTE["pizzas"].values()
                   for x in re.split(r"[,()]", d["ingredients"]) for x in x.split() if len(x) > 3}

    def _corriger_description(m):
        nom, dedans = m.group("nom"), m.group("ing")
        ref = CARTE_PAR_CLE.get(sans_accent(nom))
        if not ref or re.search(r"\d", dedans) or "," not in dedans:
            return m.group(0)
        # Une tournure éditoriale n'est pas une liste d'ingrédients : on ne
        # réécrit que si le texte en place en est bien une.
        mots = {sans_accent(x) for x in re.split(r"[\s,()]+", dedans) if len(x) > 3}
        if len(mots & INGREDIENTS) < 2:
            return m.group(0)
        vrai = ref[1]["ingredients"]
        return m.group(0) if sans_accent(dedans) == sans_accent(vrai) else \
            f'{m.group("tete")}{nom}{m.group("sep")}{vrai}{m.group("fin")}'

    noms = "|".join(sorted((re.escape(n) for n in CARTE["pizzas"]), key=len, reverse=True))
    c = re.sub(rf'(?P<tete>\b[Ll][ae] )(?P<nom>{noms})(?P<sep> \()(?P<ing>[^)]{{10,140}})(?P<fin>\))',
               _corriger_description, c)
    c = re.sub(rf'(?P<tete>\b[Ll][ae] )(?P<nom>{noms})(?P<sep> — )(?P<ing>[a-zà-ÿ][^<.]{{10,140}}?)(?P<fin>(?=\s*[<.]))',
               _corriger_description, c)

    # E13 — "4.5/5" with a decimal point in running French text.
    c = re.sub(rf'\b{re.escape(RATING)}\s*/\s*5(?!")', RATING.replace(".", ",") + "/5", c)

    # S4 — Sarrians is not served; three pages still listed it among the towns.
    c = re.sub(r'(Pernes-les-Fontaines, Mazan, Monteux, Aubignan), Sarrians(,? )', r'\1\2', c)
    c = re.sub(r', Sarrians(?=,? (et )?(Caromb|Saint-Didier|Loriol))', "", c)
    c = re.sub(r'(communes? (?:voisines?|environnantes?)[^.]{0,120}?), Sarrians\b', r'\1', c)

    # T6 — the LCEN (article 6-III) and the code de commerce (R.123-237) want
    # the RCS with its greffe, the capital, the VAT number and a named
    # publication director. All four come from the registry, not from guesswork.
    if "<h2>Éditeur du site</h2>" in c:
        E = ENTREPRISE
        bloc = ("<h2>Éditeur du site</h2>\n<p>"
                f'<strong>{E["denomination"]}</strong><br>{E["forme"]}<br>'
                f'Siège social : {E["adresse"]}<br>'
                f'SIRET : {E["siret_siege"]} · SIREN : {E["siren"]}<br>'
                f'RCS : {E["rcs"]} (immatriculée au greffe d’{E["greffe"]} le {E["immatriculation"]})<br>'
                f'TVA intracommunautaire : {E["tva"]}<br>'
                f'Directeur de la publication : {E["directeur_publication"]}<br>'
                f'Gérants : {" et ".join(E["gerants"])}<br>'
                f'Téléphone : {E["telephone"]}<br>Courriel : {EMAIL}</p>\n'
                f'<p>Le fonds de commerce est exploité depuis {E["fonds_depuis"]} ; '
                f'il a été repris par {E["denomination"]} le {E["reprise"]}.</p>\n')
        i = c.find("<h2>Éditeur du site</h2>")
        j = c.find("<h2>Hébergement</h2>", i)
        if j != -1 and "TVA intracommunautaire" not in c[i:j]:
            c = c[:i] + bloc + c[j:]
            log(rel, "mentions légales complétées (RCS, capital, TVA, directeur de publication)")
        H = E["hebergeur"]
        c = re.sub(r'(Ce site est h[ée]berg[ée] par <strong>GitHub, Inc\.</strong><br>[^<]*<br>Site : github\.com)(?!<br>Contact)',
                   rf'\1<br>Contact : {H["contact"]}', c)

    # T7 — the CGV ignored the one condition that actually blocks an order, and
    # said nothing about the withdrawal right. For meals prepared to order the
    # right does not apply, but the contract has to say so rather than omit it.
    if "<h2>8. Droit applicable</h2>" in c and "Minimum de commande" not in c:
        paliers = {}
        for nom, _cp, mini, _g in COMMUNES.values():
            paliers.setdefault(mini, []).append(nom)
        lignes = "".join(
            f"<li><strong>{m} grandes pizzas (ou {m * 2} petites)</strong> : {_liste(v)}.</li>"
            for m, v in sorted(paliers.items()))
        articles = (
            "<h2>8. Minimum de commande</h2>\n"
            "<p>La livraison est gratuite, à partir d’un minimum qui varie selon la commune :</p>\n"
            f"<ul>{lignes}</ul>\n"
            "<p>Une petite pizza (26 cm) compte pour une demi-grande (33 cm). "
            "Les commandes qui n’atteignent pas ce minimum restent possibles à emporter. "
            "Les communes non listées ne sont pas desservies : appelez-nous au "
            f"{ENTREPRISE['telephone']}.</p>\n"
            "<h2>9. Droit de rétractation</h2>\n"
            "<p>Conformément à l’article L.221-28, 3° et 4° du code de la consommation, "
            "le droit de rétractation ne s’applique pas aux denrées périssables ni aux biens "
            "confectionnés à la demande du consommateur. Nos pizzas étant préparées à la "
            "commande, votre commande est ferme dès sa confirmation téléphonique par notre "
            "équipe. Toute réclamation relève de l’article 6.</p>\n")
        c = c.replace("<h2>8. Droit applicable</h2>",
                      articles + "<h2>10. Droit applicable</h2>", 1)
        c = c.replace("<h2>9. Médiateur</h2>", "<h2>11. Médiateur</h2>", 1)
        log(rel, "CGV : minimum de commande et droit de rétractation ajoutés")

    # C1 — the online form is shut from 17h30, which is when the service
    # starts, so the main button spent the whole evening opening a refusal.
    # The owner chose to keep that behaviour and tell the truth instead: after
    # 17h30 the button says what it does, and dials straight away. Links that
    # sit inside a sentence keep their wording.
    if rel == "index.html" and "libellerCommander" not in c:
        tel = ENTREPRISE["telephone"]
        c = c.replace("</body>",
                      "<script>function libellerCommander(){var d=new Date();"
                      "if(d.getHours()*60+d.getMinutes()<17*60+30)return;"
                      "document.querySelectorAll('a[onclick*=\"openCommander\"]').forEach("
                      "function(b){var t=b.textContent.trim();"
                      "if(b.classList.contains('social-btn'))return;"
                      "if(t.indexOf('🍕')!==0&&t!=='Commander maintenant')return;"
                      # Dans la bannière le numéro est déjà affiché en grand juste
                      # au-dessus : le répéter dans le bouton le fait passer à la ligne.
                      "b.textContent=b.closest('.hero-panneau')?'📞 Appeler pour commander':"
                      f"'📞 Appeler pour commander — {tel}';"
                      f"b.setAttribute('href','tel:{tel.replace(' ', '')}');"
                      "b.setAttribute('onclick','');});}"
                      "window.addEventListener('load',libellerCommander);</script>\n</body>", 1)
        log(rel, "bouton de commande : libellé honnête après 17h30")

    # 6z7. La bande de chiffres de l'accueil. Le nombre vit dans un attribut
    # data-target et le libellé dans un élément voisin : les règles qui ne
    # traitent que le texte ne le voyaient pas, et le compteur d'avis est resté
    # à 526 pendant que les 582 du moment s'affichaient partout ailleurs. On
    # accorde donc chaque chiffre à son libellé, comme pour les minimums.
    if 'class="counter-num"' in c:
        _recettes = len(re.findall(r"\{cat:'[^']*',\s*name:", c)) or len(MENU)

        def _compteur(m):
            libelle = m.group("lbl").lower()
            if "avis" in libelle:
                neuf, lbl = COUNT, m.group("lbl")
            elif "recette" in libelle or "pizza" in libelle:
                # 80 entrées au menu, dont quatre desserts : ce ne sont pas
                # 80 pizzas. Le libellé suit le décompte réel.
                neuf, lbl = str(_recettes), "Recettes au menu"
            else:
                return m.group(0)
            return (f'{m.group("tete")}data-target="{neuf}">{neuf}</span>'
                    f'{m.group("entre")}{lbl}</span>')

        avant = c
        c = re.sub(r'(?P<tete><span class="counter-num" )data-target="\d+">\d+</span>'
                   r'(?P<entre>\s*<span class="counter-lbl">)(?P<lbl>[^<]*)</span>',
                   _compteur, c)
        if c != avant:
            log(rel, f"bande de chiffres accordée ({COUNT} avis, {_recettes} recettes)")

    # 6v2. Every page other than the homepage gets a link into the order form.
    # Before 17h30 it opens the online form; after, the homepage shows the
    # phone modal by itself, so one label has to be true in both cases.
    if (rel != "index.html" and "commander-inline" not in c
            and "</main>" in c and "noindex" not in c):
        cta = ('<p class="commander-inline" style="text-align:center;margin:2rem auto;">'
               f'<a href="{HOST}/#commander" style="display:inline-block;padding:.9rem 2rem;'
               'background:#A8202A;color:#FFFDF7;text-decoration:none;border-radius:2px;'
               'font-size:.85rem;letter-spacing:.08em;text-transform:uppercase;font-weight:600;">'
               '🍕 Commander</a></p>')
        c = c.replace("</main>", cta + "\n</main>", 1)
        log(rel, "accès au formulaire de commande ajouté")

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

# ---------- politique de confidentialité ----------
# Exigée par Google pour publier l'application « Agent Pizza Napoli » (accès Gmail,
# Drive, Sheets, Agenda du compte de la pizzeria) ; couvre aussi le site lui-même.
# Créée seulement si absente : une version retouchée à la main n'est pas écrasée.
confid = os.path.join(SITE, "confidentialite.html")
if not os.path.exists(confid):
    with open(confid, "w", encoding="utf-8") as f:
        f.write(f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Politique de confidentialité — Pizza Napoli Carpentras</title>
<meta name="description" content="Données personnelles traitées par Pizza Napoli Carpentras : commandes, mesure d'audience, et outil interne de gestion.">
<link rel="canonical" href="{HOST}/confidentialite.html">
<style>
body{{margin:0;font-family:system-ui,sans-serif;background:#FFFDF7;color:#3D3328;line-height:1.7;}}
main{{max-width:760px;margin:0 auto;padding:32px 20px 64px;}}
h1{{color:#A8202A;font-size:clamp(1.6rem,4vw,2.1rem);line-height:1.25;}}
h2{{font-size:1.15rem;margin-top:2rem;}}
a{{color:#A8202A;}}
.r{{font-size:.85rem;color:#5A5248;}}
</style></head>
<body><main>
<p class="r"><a href="{HOST}/">← Retour à l'accueil</a></p>
<h1>Politique de confidentialité</h1>
<p class="r">Dernière mise à jour : novembre 2026</p>

<h2>Qui sommes-nous</h2>
<p>Le responsable du traitement est la SARL Pizza Napoli Carpentras, 209 avenue Pierre Sémard,
84200 Carpentras (SIRET 952 676 310 00016). Contact : carpentraspizzanapoli@gmail.com,
07 61 08 36 08.</p>

<h2>Commandes passées sur le site</h2>
<p>Quand vous commandez, nous recevons votre nom, votre téléphone, votre adresse de livraison et le
contenu de la commande, transmis par e-mail via le service Web3Forms, ou par WhatsApp si vous
choisissez ce canal. Ces informations servent uniquement à préparer et livrer votre commande. Elles
sont conservées le temps nécessaire à la gestion des commandes et aux obligations comptables.</p>

<h2>Mesure d'audience</h2>
<p>Le site utilise Google Analytics uniquement si vous l'acceptez dans le bandeau de consentement.
Sans votre accord, aucun cookie de mesure n'est déposé. Vous pouvez changer d'avis à tout moment en
effaçant les données du site dans votre navigateur.</p>

<h2>Outil interne de gestion « Agent Pizza Napoli »</h2>
<p>Pizza Napoli utilise un outil interne, « Agent Pizza Napoli », qui accède avec son autorisation
au seul compte Google de la pizzeria (carpentraspizzanapoli@gmail.com) : Gmail, Google Drive,
Google Sheets et Google Agenda. Il sert exclusivement à la gestion de l'entreprise : lecture des
tickets de caisse et des factures fournisseurs, classement des e-mails, préparation de brouillons de
réponse, archivage des documents, suivi du chiffre d'affaires et des échéances. Il n'est ni proposé
ni accessible au public.</p>
<p>Les e-mails et documents lus peuvent être analysés par le service d'intelligence artificielle
Claude (Anthropic) pour être classés et résumés. Ces données ne sont ni vendues, ni cédées, ni
utilisées à des fins publicitaires.</p>
<p>L'utilisation et le transfert vers toute autre application des informations reçues des API
Google respectent la <a href="https://developers.google.com/terms/api-services-user-data-policy">politique
relative aux données utilisateur des services API Google</a>, y compris les exigences d'utilisation
limitée (« Limited Use »).</p>
<p>Cet accès peut être retiré à tout moment depuis
<a href="https://myaccount.google.com/permissions">les autorisations du compte Google</a>.</p>

<h2>Vos droits</h2>
<p>Vous disposez d'un droit d'accès, de rectification, d'effacement, d'opposition et de limitation
du traitement de vos données. Écrivez-nous à carpentraspizzanapoli@gmail.com. Vous pouvez aussi
adresser une réclamation à la CNIL (<a href="https://www.cnil.fr">www.cnil.fr</a>).</p>
</main></body></html>
''')
    print("  [confidentialite.html] politique de confidentialité créée")

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
