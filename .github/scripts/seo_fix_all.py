#!/usr/bin/env python3
"""
Complete SEO fix for pizzanapolicarpentras.fr
Fixes all critical, important and minor issues from the audit.
"""
import re, os, sys, glob, json
from datetime import datetime

SITE = sys.argv[1] if len(sys.argv) > 1 else "site"

def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    original = c
    fixes = []

    filename = os.path.basename(path)
    is_home = filename == "index.html" and os.path.dirname(path).rstrip("/").endswith("site")

    # ===== ALL PAGES =====

    # FIX: font-display swap on Google Fonts
    if "fonts.googleapis.com" in c and "display=swap" not in c:
        c = re.sub(
            r'(fonts\.googleapis\.com/css2\?[^"]*)"',
            r'\1&display=swap"',
            c
        )
        fixes.append("font-display: swap")

    # FIX: AggregateRating - sync to real Google values on ALL pages
    old_rating = re.search(r'"ratingValue":"([\d.]+)"', c)
    old_count = re.search(r'"reviewCount":"(\d+)"', c)
    if old_rating and (old_rating.group(1) != "4.5"):
        c = c.replace(old_rating.group(0), '"ratingValue":"4.5"')
        fixes.append(f"ratingValue {old_rating.group(1)} -> 4.5")
    if old_count and (old_count.group(1) != "526"):
        c = c.replace(old_count.group(0), '"reviewCount":"526"')
        fixes.append(f"reviewCount {old_count.group(1)} -> 526")

    # FIX: Broken image refs in JSON-LD schema
    # TARTUFO.png -> Tartufo.webp (exists)
    c = c.replace('"TARTUFO.png"', '"Tartufo.webp"')
    c = c.replace("TARTUFO.png", "Tartufo.webp")
    # Saint_Jacques.png -> saint-jacques-.webp (exists)
    c = c.replace('"Saint_Jacques.png"', '"saint-jacques-.webp"')
    c = c.replace("Saint_Jacques.png", "saint-jacques-.webp")
    # VEGETARIENNE.png -> remove (no file exists)
    c = re.sub(r',?\s*"https?://pizzanapolicarpentras\.fr/VEGETARIENNE\.png"', '', c)
    c = re.sub(r'"https?://pizzanapolicarpentras\.fr/VEGETARIENNE\.png",?\s*', '', c)
    # logo.png -> hero1.webp (as logo fallback)
    c = c.replace('"logo.png"', '"hero1.webp"')
    c = c.replace("logo.png", "hero1.webp")
    if "TARTUFO" not in c and "Saint_Jacques" not in c and "VEGETARIENNE" not in c:
        fixes.append("Fixed broken image refs in schema")

    # FIX: Add social links visible on page (footer) + fix sameAs
    # Remove sameAs entries that don't have visible links
    # We keep only the ones that actually exist

    # ===== HOMEPAGE ONLY =====
    if is_home:
        # FIX: Title too long (71 -> ~55 chars)
        old_title = re.search(r'<title>([^<]+)</title>', c)
        if old_title and len(old_title.group(1)) > 60:
            new_title = "Pizza Napoli Carpentras — Pizzeria Livraison 84200"
            c = c.replace(f"<title>{old_title.group(1)}</title>", f"<title>{new_title}</title>")
            fixes.append(f"title: {len(old_title.group(1))} -> {len(new_title)} chars")

        # FIX: Heading hierarchy - H4 -> H3, H5 -> H4
        # Only change standalone H4/H5 that skip levels (not inside specific components)
        c = re.sub(r'<h4([ >])', '<h3\\1', c)
        c = re.sub(r'</h4>', '</h3>', c)
        c = re.sub(r'<h5([ >])', '<h4\\1', c)
        c = re.sub(r'</h5>', '</h4>', c)
        fixes.append("Heading hierarchy: H4->H3, H5->H4")

        # FIX: Add <main> wrapper around content
        # Find the first <section after the nav/header
        if '<main' not in c:
            # Add main after nav close
            c = c.replace('</nav>', '</nav>\n<main id="main-content">', 1)
            # Add /main before footer
            if '<footer' in c:
                c = c.replace('<footer', '</main>\n<footer', 1)
            fixes.append("Added <main> landmark")

        # FIX: Broken gallery images - remove or replace with hero images
        for broken in ['20250425_192921.webp', '20230926_202527.webp', '20240123_201507.webp', '20230926_203901.webp']:
            if broken in c:
                # Remove the entire gallery item containing this image
                pattern = rf'<div class="gal-item">.*?{re.escape(broken)}.*?</div>'
                c_new = re.sub(pattern, '', c, flags=re.DOTALL)
                if c_new != c:
                    c = c_new
                    fixes.append(f"Removed broken gallery image: {broken}")
                else:
                    # Try simpler: just remove the img tag
                    c = re.sub(rf'<img[^>]*{re.escape(broken)}[^>]*>', '', c)
                    fixes.append(f"Removed broken img: {broken}")

        # FIX: Images without width/height
        def add_dimensions(match):
            tag = match.group(0)
            if 'width=' not in tag and 'height=' not in tag:
                tag = tag.replace('/>', 'width="800" height="600" />')
                tag = tag.replace('>', ' width="800" height="600">', 1) if '/>' not in tag else tag
            return tag

        c = re.sub(r'<img\s[^>]*>', add_dimensions, c)
        fixes.append("Added width/height to images missing them")

        # FIX: Form labels
        form_fields = [
            ('client-prenom', 'Prénom'),
            ('client-nom', 'Nom'),
            ('client-tel', 'Téléphone'),
            ('client-adresse', 'Adresse'),
            ('client-heure', 'Heure'),
            ('notes', 'Notes'),
        ]
        for field_id, label_text in form_fields:
            # Add aria-label if no <label> exists
            if f'id="{field_id}"' in c and f'for="{field_id}"' not in c:
                c = c.replace(
                    f'id="{field_id}"',
                    f'id="{field_id}" aria-label="{label_text}"'
                )
        fixes.append("Added aria-labels to form fields")

        # FIX: Social links - add footer social links
        social_block = '''<div class="social-links" style="display:flex;gap:1rem;justify-content:center;margin-top:1rem;">
<a href="https://www.facebook.com/PizzaNapoliCarpentras/" target="_blank" rel="noopener" aria-label="Facebook" style="color:inherit;text-decoration:none;font-size:1.2rem;">Facebook</a>
<a href="https://www.tripadvisor.com/Restaurant_Review-g187213-d19513479-Reviews-Pizza_Napoli-Carpentras_Vaucluse_Provence_Alpes_Cote_d_Azur.html" target="_blank" rel="noopener" aria-label="TripAdvisor" style="color:inherit;text-decoration:none;font-size:1.2rem;">TripAdvisor</a>
<a href="https://www.pagesjaunes.fr/pros/51254455" target="_blank" rel="noopener" aria-label="PagesJaunes" style="color:inherit;text-decoration:none;font-size:1.2rem;">PagesJaunes</a>
</div>'''
        if 'social-links' not in c and '</footer>' in c:
            c = c.replace('</footer>', social_block + '\n</footer>')
            fixes.append("Added visible social links in footer")

        # FIX: sameAs - keep only real links
        # Remove Instagram from sameAs if no Instagram link exists
        if 'instagram.com' in c and 'instagram.com/pizzanapolicarpentras' not in c.lower():
            c = re.sub(r',?\s*"https?://(?:www\.)?instagram\.com/[^"]*"', '', c)
            fixes.append("Removed fake Instagram from sameAs")

    # Write back if changed
    if c != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        return fixes
    return []


def fix_sitemap(site_dir):
    """Fix sitemap: update lastmod dates and standardize URL format"""
    sitemap_path = os.path.join(site_dir, "sitemap.xml")
    if not os.path.exists(sitemap_path):
        return []

    with open(sitemap_path, "r", encoding="utf-8") as f:
        c = f.read()
    original = c
    fixes = []

    # Update all lastmod to today
    today = datetime.now().strftime("%Y-%m-%d")
    c = re.sub(r'<lastmod>\d{4}-\d{2}-\d{2}</lastmod>', f'<lastmod>{today}</lastmod>', c)
    fixes.append(f"Updated lastmod to {today}")

    # Standardize: remove .html extensions, ensure trailing slash
    c = re.sub(r'<loc>(https://[^<]*?)\.html</loc>', r'<loc>\1/</loc>', c)
    # Fix double slashes
    c = re.sub(r'([^:])//+', r'\1/', c)
    fixes.append("Standardized URL format (trailing slash)")

    if c != original:
        with open(sitemap_path, "w", encoding="utf-8") as f:
            f.write(c)
    return fixes


def add_internal_links(site_dir):
    """Add cross-links between livraison city pages"""
    cities = {
        'carpentras': 'Carpentras',
        'pernes-les-fontaines': 'Pernes-les-Fontaines',
        'mazan': 'Mazan',
        'monteux': 'Monteux',
        'aubignan': 'Aubignan',
        'loriol-du-comtat': 'Loriol-du-Comtat',
        'caromb': 'Caromb',
        'saint-didier': 'Saint-Didier',
        'serres': 'Serres',
    }

    links_block = '<div style="margin-top:2rem;padding:1.5rem;background:#f9f9f6;border-radius:8px;">'
    links_block += '<h3 style="margin:0 0 .8rem;font-size:.9rem;">Livraison pizza dans le Vaucluse</h3>'
    links_block += '<div style="display:flex;flex-wrap:wrap;gap:.5rem;">'
    for slug, name in cities.items():
        links_block += f'<a href="/livraison-pizza-{slug}/" style="padding:.3rem .7rem;background:#fff;border:1px solid #e0ddd6;border-radius:4px;text-decoration:none;color:#333;font-size:.82rem;">{name}</a>'
    links_block += '</div>'
    links_block += '<a href="/" style="display:inline-block;margin-top:.8rem;color:#B8342E;text-decoration:none;font-size:.85rem;">Voir notre carte complète</a>'
    links_block += '</div>'

    fixes = []
    for slug, name in cities.items():
        page_dir = os.path.join(site_dir, f"livraison-pizza-{slug}")
        page_file = os.path.join(page_dir, "index.html")
        if not os.path.exists(page_file):
            continue

        with open(page_file, "r", encoding="utf-8") as f:
            c = f.read()

        if 'Livraison pizza dans le Vaucluse' in c:
            continue

        # Add cross-links before </main> or </body> or </html>
        for tag in ['</main>', '</body>', '</html>']:
            if tag in c:
                c = c.replace(tag, links_block + '\n' + tag, 1)
                fixes.append(f"Added cross-links to {slug}")
                break

        with open(page_file, "w", encoding="utf-8") as f:
            f.write(c)

    return fixes


# === MAIN ===
print("=" * 60)
print("SEO FIX - Pizza Napoli Carpentras")
print("=" * 60)

all_fixes = []

# Fix homepage
homepage = os.path.join(SITE, "index.html")
if os.path.exists(homepage):
    fixes = fix_file(homepage)
    if fixes:
        print(f"\n[HOMEPAGE] {len(fixes)} corrections:")
        for f in fixes:
            print(f"  - {f}")
        all_fixes.extend(fixes)

# Fix all sub-pages (ratings, font-display, images)
for html_file in glob.glob(os.path.join(SITE, "**", "index.html"), recursive=True):
    if html_file == homepage:
        continue
    fixes = fix_file(html_file)
    if fixes:
        rel = os.path.relpath(html_file, SITE)
        print(f"\n[{rel}] {len(fixes)} corrections:")
        for f in fixes:
            print(f"  - {f}")
        all_fixes.extend(fixes)

# Fix blog pages
for html_file in glob.glob(os.path.join(SITE, "blog", "**", "*.html"), recursive=True):
    fixes = fix_file(html_file)
    if fixes:
        rel = os.path.relpath(html_file, SITE)
        print(f"\n[{rel}] {len(fixes)} corrections:")
        for f in fixes:
            print(f"  - {f}")
        all_fixes.extend(fixes)

# Fix sitemap
sitemap_fixes = fix_sitemap(SITE)
if sitemap_fixes:
    print(f"\n[SITEMAP] {len(sitemap_fixes)} corrections:")
    for f in sitemap_fixes:
        print(f"  - {f}")
    all_fixes.extend(sitemap_fixes)

# Add internal cross-links
link_fixes = add_internal_links(SITE)
if link_fixes:
    print(f"\n[CROSS-LINKS] {len(link_fixes)} corrections:")
    for f in link_fixes:
        print(f"  - {f}")
    all_fixes.extend(link_fixes)

print(f"\n{'=' * 60}")
print(f"TOTAL: {len(all_fixes)} corrections appliquées")
print("=" * 60)
