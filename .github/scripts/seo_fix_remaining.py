#!/usr/bin/env python3
"""
Fix remaining SEO issues from audit:
1. Heading hierarchy: info H3s -> H4 (after H1, before first H2)
2. Features H4s -> H3 (after H2)
3. Cannibalization: add canonical to competing pages
4. Date 2008 vs 2010: fix blog pages
5. HTTP->HTTPS: add canonical with https
"""
import re, os, sys, glob

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"
fixes = []

def log(msg):
    fixes.append(msg)
    print(f"  {msg}")

# ======================================================
# 1. HOMEPAGE: Fix heading hierarchy
# ======================================================
homepage = os.path.join(SITE, "index.html")
if os.path.exists(homepage):
    with open(homepage, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c

    # The info block (Adresse, Téléphone, Horaires, Note Google) uses H3 right after H1
    # These should be H2 (or better: keep as styled divs, but H2 is the quick SEO fix)
    # BUT there are already H2s for sections. The real fix:
    # - Info block H3s (before first H2) should become <h4> since they're sub-items of the hero
    #   Actually no - they come right after H1, so they should be H2 level.
    #   But semantically they're minor labels. Best: make them <strong> with class, not headings.

    # Strategy: Replace the info-block headings with non-heading elements
    # "Adresse", "Téléphone", "Horaires", "Note Google" are just labels
    info_labels = ['Adresse', 'Téléphone', 'Horaires', 'Note Google']
    for label in info_labels:
        c = c.replace(f'<h3>{label}</h3>', f'<strong class="info-label">{label}</strong>')
        c = c.replace(f'<h4>{label}</h4>', f'<strong class="info-label">{label}</strong>')

    # Features H4s (Ingrédients frais, Pâte maison, etc.) after H2 should be H3
    feature_labels = ['Ingrédients frais', 'Pâte maison', 'Livraison rapide', 'À emporter',
                      'Ingredients frais', 'Pate maison']
    for label in feature_labels:
        # h4 with content containing label -> h3
        pattern = rf'<h4([^>]*)>([^<]*{re.escape(label)}[^<]*)</h4>'
        replacement = rf'<h3\1>\2</h3>'
        c, n = re.subn(pattern, replacement, c)

    if c != orig:
        log("Homepage: Fixed heading hierarchy (info labels -> <strong>, features H4->H3)")

    # Add CSS for info-label if not present
    if 'info-label' in c and '.info-label' not in c:
        c = c.replace('</style>', '.info-label{display:block;font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--or,#C5A572);margin-bottom:.3rem;}\n</style>', 1)
        log("Homepage: Added .info-label CSS")

    with open(homepage, "w", encoding="utf-8") as f:
        f.write(c)

# ======================================================
# 2. CANNIBALIZATION: Add canonical to competing pages
# ======================================================
# /livraison-pizza-84200/ -> canonical to /livraison-pizza-carpentras/
# /pizza-carpentras/ -> canonical to /pizzeria-carpentras/
canonicals = {
    "livraison-pizza-84200": "https://pizzanapolicarpentras.fr/livraison-pizza-carpentras/",
    "pizza-carpentras": "https://pizzanapolicarpentras.fr/pizzeria-carpentras/",
}

for slug, canonical_url in canonicals.items():
    page_file = os.path.join(SITE, slug, "index.html")
    if not os.path.exists(page_file):
        continue

    with open(page_file, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c

    # Replace existing canonical or add one
    if 'rel="canonical"' in c:
        c = re.sub(
            r'<link rel="canonical" href="[^"]*"',
            f'<link rel="canonical" href="{canonical_url}"',
            c
        )
    elif '</head>' in c:
        c = c.replace('</head>', f'<link rel="canonical" href="{canonical_url}">\n</head>')
    elif '<head>' in c:
        c = c.replace('<head>', f'<head>\n<link rel="canonical" href="{canonical_url}">')

    if c != orig:
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(c)
        log(f"Canonical: {slug}/ -> {canonical_url}")

# ======================================================
# 3. FIX DATE 2010 -> 2008 in blog pages
# ======================================================
for html_file in glob.glob(os.path.join(SITE, "blog", "**", "*.html"), recursive=True):
    with open(html_file, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c

    # Replace "depuis 2010" with "depuis 2008"
    c = c.replace("depuis 2010", "depuis 2008")
    c = c.replace("Depuis 2010", "Depuis 2008")
    # Replace "en 2010" context about founding
    c = re.sub(r'(?:fondée?|créée?|ouverte?|née?)\s+en\s+2010', lambda m: m.group(0).replace('2010', '2008'), c, flags=re.IGNORECASE)

    if c != orig:
        rel = os.path.relpath(html_file, SITE)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(c)
        log(f"Date fix: {rel} (2010 -> 2008)")

# Also fix blog index pages
for html_file in glob.glob(os.path.join(SITE, "blog", "*", "index.html"), recursive=True):
    with open(html_file, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c
    c = c.replace("depuis 2010", "depuis 2008")
    c = c.replace("Depuis 2010", "Depuis 2008")
    c = re.sub(r'(?:fondée?|créée?|ouverte?|née?)\s+en\s+2010', lambda m: m.group(0).replace('2010', '2008'), c, flags=re.IGNORECASE)
    if c != orig:
        rel = os.path.relpath(html_file, SITE)
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(c)
        log(f"Date fix: {rel} (2010 -> 2008)")

# ======================================================
# 4. HOMEPAGE: Fix "Commander" CTA clarity
# ======================================================
if os.path.exists(homepage):
    with open(homepage, "r", encoding="utf-8") as f:
        c = f.read()
    orig = c

    # Nav CTA: keep short
    # Main CTAs: clarify it's WhatsApp
    c = c.replace(
        '>🍕 Commander en ligne</a>',
        '>🍕 Commander par WhatsApp</a>'
    )
    # The "Composer ma commande" is good, keep it

    if c != orig:
        with open(homepage, "w", encoding="utf-8") as f:
            f.write(c)
        log("Homepage: CTA 'Commander en ligne' -> 'Commander par WhatsApp'")

# ======================================================
# SUMMARY
# ======================================================
print(f"\n{'='*50}")
print(f"Total: {len(fixes)} corrections")
print("="*50)
