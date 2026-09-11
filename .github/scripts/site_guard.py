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

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
HOST = "https://pizzanapolicarpentras.fr"
FACEBOOK = "https://www.facebook.com/PizzaNapoliCarpentras/"
FOUNDED = "2008"
DUPLICATES = {  # page -> canonical target (content cannibalization)
    "livraison-pizza-84200": "livraison-pizza-carpentras",
    "pizza-carpentras": "pizzeria-carpentras",
}
EXCLUDE_FROM_SITEMAP = {"redirect", "404", "google", "mentions-legales-old", "photos-finales", "photos-preview"}
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

def git_lastmod(path):
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
    for tag in set(re.findall(r'<img\s[^>]*>', c)):
        src = re.search(r'src="([^"]+)"', tag)
        if src and not exists_local(src.group(1), base_dir):
            fixed = repair_ref(src.group(1), base_dir)
            if fixed:
                c = c.replace(tag, tag.replace(f'src="{src.group(1)}"', f'src="{fixed}"'))
                log(rel, f"<img {src.group(1)}> introuvable -> réparé en {fixed}")
            else:
                c = c.replace(tag, "")
                log(rel, f"<img {src.group(1)}> introuvable, aucun remplaçant -> retirée")

    # 6. landmark + fonts
    if "<main" not in c and "</nav>" in c:
        c = c.replace("</nav>", '</nav>\n<main id="main-content">', 1)
        c = c.replace("<footer", "</main>\n<footer", 1) if "<footer" in c else c.replace("</body>", "</main>\n</body>", 1)
    c = re.sub(r'(fonts\.googleapis\.com/css2\?[^"]*?)(?<!display=swap)"', lambda mm: mm.group(1) + ("" if "display=swap" in mm.group(1) else "&display=swap") + '"', c)

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
    entries.append((url, git_lastmod(path) or "2026-09-11", freq, prio))

entries.sort(key=lambda e: (e[0] != f"{HOST}/", "/blog/" in e[0], e[0]))
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for url, lastmod, freq, prio in entries:
    xml += ["  <url>", f"    <loc>{url}</loc>", f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{freq}</changefreq>", f"    <priority>{prio}</priority>", "  </url>"]
xml.append("</urlset>\n")
new_sitemap = "\n".join(xml)
smap = os.path.join(SITE, "sitemap.xml")
old = open(smap, encoding="utf-8").read() if os.path.exists(smap) else ""
if old != new_sitemap:
    with open(smap, "w", encoding="utf-8") as f:
        f.write(new_sitemap)
    log("sitemap.xml", f"régénéré depuis le disque : {len(entries)} URLs")

print(f"\n{len(report)} changement(s)" if report else "\nAucun changement — site conforme")
