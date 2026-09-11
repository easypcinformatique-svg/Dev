#!/usr/bin/env python3
"""
Auto-sync Google reviews (rating + count) into the pizzeria website.
Tries Google Places API first, falls back to scraping.
"""
import re, os, sys, json, urllib.request, urllib.error

SITE_PATH = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

# --- 1. Fetch real Google data ---

rating = None
count = None

# Method 1: Google Places API (New) - most reliable
api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
place_id = os.environ.get("GOOGLE_PLACE_ID", "")

if api_key and place_id:
    print("[Places API] Fetching reviews...")
    try:
        url = f"https://places.googleapis.com/v1/places/{place_id}?fields=rating,userRatingCount&key={api_key}"
        req = urllib.request.Request(url)
        req.add_header("X-Goog-Api-Key", api_key)
        req.add_header("X-Goog-FieldMask", "rating,userRatingCount")
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode())
        if "rating" in data:
            rating = round(data["rating"], 1)
            count = data.get("userRatingCount", 0)
            print(f"[Places API] Got: {rating}/5 - {count} avis")
    except Exception as e:
        print(f"[Places API] Error: {e}")

# Method 2: Legacy Places API
if rating is None and api_key and place_id:
    print("[Legacy API] Trying legacy endpoint...")
    try:
        url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&fields=rating,user_ratings_total&key={api_key}"
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read().decode())
        result = data.get("result", {})
        if "rating" in result:
            rating = round(result["rating"], 1)
            count = result.get("user_ratings_total", 0)
            print(f"[Legacy API] Got: {rating}/5 - {count} avis")
    except Exception as e:
        print(f"[Legacy API] Error: {e}")

# Method 3: Scrape from third-party aggregator sites
if rating is None:
    print("[Scraping] Trying restaurantguru.com...")
    try:
        req = urllib.request.Request(
            "https://restaurantguru.com/Pechoux-Guillaume-Carpentras",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'Google[^<]*?(\d\.\d)\s*/\s*5[^<]*?(\d+)\s*(?:review|avis)', html, re.IGNORECASE)
        if m:
            rating = float(m.group(1))
            count = int(m.group(2))
            print(f"[Scraping] Got: {rating}/5 - {count} avis")
    except Exception as e:
        print(f"[Scraping restaurantguru] Error: {e}")

# Method 4: Try Eater Space
if rating is None:
    print("[Scraping] Trying eater.space...")
    try:
        req = urllib.request.Request(
            "https://eater.space/pizza-napoli-carpentras",
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'(\d\.\d)\s*(?:/5|stars?)[^<]*?(\d+)\s*(?:review|avis)', html, re.IGNORECASE)
        if m:
            rating = float(m.group(1))
            count = int(m.group(2))
            print(f"[Scraping eater.space] Got: {rating}/5 - {count} avis")
    except Exception as e:
        print(f"[Scraping eater.space] Error: {e}")

# Method 5: Environment variables override (manual fallback)
env_rating = os.environ.get("OVERRIDE_RATING")
env_count = os.environ.get("OVERRIDE_COUNT")
if env_rating and env_count:
    rating = float(env_rating)
    count = int(env_count)
    print(f"[Override] Using manual values: {rating}/5 - {count} avis")

if rating is None or count is None:
    print("ERROR: Could not fetch Google reviews from any source.")
    print("Set GOOGLE_PLACES_API_KEY + GOOGLE_PLACE_ID secrets,")
    print("or use OVERRIDE_RATING + OVERRIDE_COUNT as fallback.")
    sys.exit(1)

# Format rating
rating_str = f"{rating:.1f}" if isinstance(rating, float) else str(rating)
count_str = str(count)

print(f"\n=== Updating site with: {rating_str}/5 - {count_str} avis ===\n")

# --- 2. Read site ---

with open(SITE_PATH, "r", encoding="utf-8") as f:
    c = f.read()

changes = 0

# --- 3. Update all occurrences ---

# JSON-LD AggregateRating
old = re.search(r'"ratingValue":"[\d.]+"', c)
if old:
    new_val = f'"ratingValue":"{rating_str}"'
    if old.group(0) != new_val:
        c = c.replace(old.group(0), new_val)
        changes += 1
        print(f"  JSON-LD ratingValue: {old.group(0)} -> {new_val}")

old = re.search(r'"reviewCount":"\d+"', c)
if old:
    new_val = f'"reviewCount":"{count_str}"'
    if old.group(0) != new_val:
        c = c.replace(old.group(0), new_val)
        changes += 1
        print(f"  JSON-LD reviewCount: {old.group(0)} -> {new_val}")

# Hero badge animated counter
old = re.search(r'animCounter\(r,([\d.]+),', c)
if old:
    new_val = f'animCounter(r,{rating_str},'
    if old.group(0) != new_val:
        c = c.replace(old.group(0), new_val)
        changes += 1
        print(f"  Hero badge: {old.group(1)} -> {rating_str}")

# Info section: X.X/5 — NNN avis clients
c_new, n = re.subn(
    r'(Note Google</h4><p>)[\d.]+/5\s*[—–-]\s*\d+\s*avis clients',
    f'\\g<1>{rating_str}/5 — {count_str} avis clients',
    c
)
if n and c_new != c:
    c = c_new; changes += n
    print(f"  Info section: {n} fix(es)")

# Testimonials: X.X/5 basé sur <strong>NNN avis Google vérifiés</strong>
c_new, n = re.subn(
    r'[\d.]+/5 basé sur\s*<strong>\d+ avis Google vérifiés</strong>',
    f'{rating_str}/5 basé sur <strong>{count_str} avis Google vérifiés</strong>',
    c
)
if n and c_new != c:
    c = c_new; changes += n
    print(f"  Testimonials: {n} fix(es)")

# Meta descriptions: notée X.X/5 sur Google par plus de NNN clients
c_new, n = re.subn(
    r'notée ((?:<strong>)?)[\d.]+/5 sur Google((?:</strong>)?)\s*par plus de \d+ clients',
    f'notée \\g<1>{rating_str}/5 sur Google\\g<2> par plus de {count_str} clients',
    c
)
if n and c_new != c:
    c = c_new; changes += n
    print(f"  Meta/about text: {n} fix(es)")

# Counter target for review count - also fix broken HTML structure
# The counter may be malformed: data-target="422" Google</span> (missing >0< and label)
broken = re.search(r'<span class="counter-num" data-target="\d+"[^>]*Google</span>', c)
if broken:
    fixed = f'<span class="counter-num" data-target="{count_str}">0</span><span class="counter-lbl">Avis Google</span>'
    c = c.replace(broken.group(0), fixed)
    changes += 1
    print(f"  Fixed broken counter HTML + target -> {count_str}")
else:
    old = re.search(r'data-target="(\d+)"(>0</span><span class="counter-lbl">Avis Google)', c)
    if old and old.group(1) != count_str:
        c = c.replace(old.group(0), f'data-target="{count_str}"{old.group(2)}')
        changes += 1
        print(f"  Counter target: {old.group(1)} -> {count_str}")

# Generic "NNN avis" near Google context (careful, only near Google mentions)
for pattern in [r'>\s*(\d{3,4})\s*<[^>]*>\s*AVIS\s*GOOGLE']:
    for m in re.finditer(pattern, c):
        old_count = m.group(1)
        if old_count != count_str:
            c = c.replace(m.group(0), m.group(0).replace(old_count, count_str))
            changes += 1
            print(f"  AVIS GOOGLE counter: {old_count} -> {count_str}")

print(f"\nHomepage changes: {changes}")

# --- 4. Write back ---
with open(SITE_PATH, "w", encoding="utf-8") as f:
    f.write(c)

# --- 5. Fix ALL sub-pages too (prevent rating inconsistency) ---
import glob
site_dir = os.path.dirname(SITE_PATH)
sub_changes = 0
for html_file in glob.glob(os.path.join(site_dir, "**", "index.html"), recursive=True):
    if os.path.abspath(html_file) == os.path.abspath(SITE_PATH):
        continue
    with open(html_file, "r", encoding="utf-8") as f:
        sc = f.read()
    sc_orig = sc
    old_r = re.search(r'"ratingValue":"[\d.]+"', sc)
    if old_r and old_r.group(0) != f'"ratingValue":"{rating_str}"':
        sc = sc.replace(old_r.group(0), f'"ratingValue":"{rating_str}"')
    old_c = re.search(r'"reviewCount":"\d+"', sc)
    if old_c and old_c.group(0) != f'"reviewCount":"{count_str}"':
        sc = sc.replace(old_c.group(0), f'"reviewCount":"{count_str}"')
    if sc != sc_orig:
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(sc)
        sub_changes += 1
        rel = os.path.relpath(html_file, site_dir)
        print(f"  Sub-page synced: {rel}")

total = changes + sub_changes
if total > 0:
    print(f"\nSite updated to {rating_str}/5 - {count_str} avis Google ({changes} homepage + {sub_changes} sub-pages)")
else:
    print("Site already up to date, no changes needed")

sys.exit(0)
