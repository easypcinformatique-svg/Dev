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
print(f"Source of truth: {RATING}/5 — {COUNT} avis\n")

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

    # 6d. repair damage left by earlier one-shot scripts
    if '<div class="galerie-grid"> </div>' in c:
        i = c.find('<div class="galerie-grid">')
        j = c.find('<div style="text-align:center;padding:1rem;font-size:.75rem', i)
        if i != -1 and j != -1:
            c = c[:i] + GALLERY + "\n" + c[j:]
            log(rel, "galerie reconstruite (4 vignettes perdues par un script)")
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
