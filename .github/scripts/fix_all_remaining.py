import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

changes = []

# 1. Fix font-display - Google Fonts URL already has display=swap
# Add font-display:swap to any inline @font-face
if "font-display" not in c:
    # Check if Google Fonts URL has display=swap
    if "display=swap" in c:
        changes.append("font-display: already in Google Fonts URL (display=swap)")
    else:
        c = c.replace("fonts.googleapis.com/css2?", "fonts.googleapis.com/css2?display=swap&")
        changes.append("Added display=swap to Google Fonts URL")

# 3+4. Remove serviceWorker registration (sw.js doesn't exist and can't be deployed)
if "serviceWorker" in c:
    c = re.sub(r"<script>if\('serviceWorker'[^<]*</script>", "", c)
    changes.append("Removed serviceWorker registration (sw.js 404)")

# 5. Fix OG image: hero1.jpg -> hero1.webp
c = c.replace('content="https://pizzanapolicarpentras.fr/hero1.jpg"', 'content="https://pizzanapolicarpentras.fr/hero1.webp"')
changes.append("Fixed OG image: hero1.jpg -> hero1.webp")

# 6. Fix preload hero: hero1.jpg -> hero1.webp
c = c.replace('href="hero1.jpg"', 'href="hero1.webp"')
c = c.replace("href='hero1.jpg'", "href='hero1.webp'")
changes.append("Fixed preload hero: hero1.jpg -> hero1.webp")

# 9. Fix duplicated width/height attributes
# Pattern: width="X" height="Y" ... width="X" height="Y"
c = re.sub(r'(width="\d+" height="\d+")(.*?)(width="\d+" height="\d+")', r'\1\2', c, count=5)
# Also fix: src="X" width="W" height="H" srcset="X" type="image/webp" ... loading="lazy" width="W" height="H"
c = re.sub(r'loading="lazy" width="\d+" height="\d+">', 'loading="lazy">', c)
changes.append("Fixed duplicated width/height on images")

# 10. Fix external links without target="_blank" (tripadvisor, pagesjaunes)
for domain in ["tripadvisor.com", "pagesjaunes.fr"]:
    pattern = r'href="(https?://[^"]*' + re.escape(domain) + r'[^"]*)"(?!\s*target)'
    replacement = r'href="\1" target="_blank" rel="noopener"'
    c, n = re.subn(pattern, replacement, c)
    if n > 0:
        changes.append(f"Added target=_blank to {domain} links ({n}x)")

print(f"Total changes: {len(changes)}")
for ch in changes:
    print(f"  - {ch}")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
