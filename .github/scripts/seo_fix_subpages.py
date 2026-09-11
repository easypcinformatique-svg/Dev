#!/usr/bin/env python3
"""Fix sub-page SEO issues: visible rating text, og:image, foundingDate, <main>, sitemap guide URLs."""
import re, os, sys, glob

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
RATING_COMMA, RATING_DOT, COUNT = "4,5", "4.5", "526"

total = 0
for path in glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True):
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c
    fixes = []

    # Visible rating text (x,x/5 or x.x/5)
    c, n = re.subn(r'\b[1-5],\d\s*/\s*5\b', f'{RATING_COMMA}/5', c)
    if n: fixes.append(f"note visible x,x/5 -> {RATING_COMMA}/5 ({n})")
    c, n = re.subn(r'\b[1-5]\.\d\s*/\s*5\b(?![\d"])', f'{RATING_DOT}/5', c)
    if n: fixes.append(f"note visible x.x/5 -> {RATING_DOT}/5 ({n})")
    c, n = re.subn(r'note\s+[1-5][,.]\d\b', f'note {RATING_COMMA}', c)
    if n: fixes.append(f"'note x,x' ({n})")

    # Visible review count
    c, n = re.subn(r'\b(?:272|306|422|520|524)\s+avis', f'{COUNT} avis', c)
    if n: fixes.append(f"nb avis -> {COUNT} ({n})")

    # foundingDate / 2010
    c, n = re.subn(r'"foundingDate":"2010"', '"foundingDate":"2008"', c)
    if n: fixes.append("foundingDate 2010 -> 2008")
    c, n = re.subn(r'\b(depuis|en|dès)\s+2010\b', r'\1 2008', c, flags=re.IGNORECASE)
    if n: fixes.append(f"texte 2010 -> 2008 ({n})")

    # og:image hero1.jpg (404) -> hero1.webp
    c, n = re.subn(r'hero1\.jpg', 'hero1.webp', c)
    if n: fixes.append("og:image .jpg -> .webp")

    # <main> landmark
    if "<main" not in c and "</nav>" in c:
        c = c.replace("</nav>", '</nav>\n<main id="main-content">', 1)
        if "<footer" in c:
            c = c.replace("<footer", "</main>\n<footer", 1)
        else:
            c = c.replace("</body>", "</main>\n</body>", 1)
        fixes.append("<main> ajouté")

    if c != orig:
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        total += len(fixes)
        print(f"[{os.path.relpath(path, SITE)}] " + "; ".join(fixes))

# Sitemap: guide pages only exist as .html — restore correct URLs
smap = os.path.join(SITE, "sitemap.xml")
if os.path.exists(smap):
    with open(smap, "r", encoding="utf-8") as f:
        s = f.read()
    s2, n = re.subn(r'<loc>(https://pizzanapolicarpentras\.fr/blog/guide-[a-z-]+)/</loc>', r'<loc>\1.html</loc>', s)
    if n:
        with open(smap, "w", encoding="utf-8") as f:
            f.write(s2)
        total += n
        print(f"[sitemap.xml] {n} URLs guide-*.html restaurées")

print(f"\nTotal: {total} corrections")
