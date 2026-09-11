import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

changes = 0

# Real Google values (confirmed by owner)
REAL_RATING = "4.5"
REAL_COUNT = "526"

# 1. JSON-LD AggregateRating: "ratingValue":"4.5","reviewCount":"524"
old = re.search(r'"ratingValue":"[\d.]+"', c)
if old:
    c = c.replace(old.group(0), f'"ratingValue":"{REAL_RATING}"')
    changes += 1
    print(f"Fixed JSON-LD ratingValue: {old.group(0)} -> {REAL_RATING}")

old = re.search(r'"reviewCount":"[\d]+"', c)
if old:
    c = c.replace(old.group(0), f'"reviewCount":"{REAL_COUNT}"')
    changes += 1
    print(f"Fixed JSON-LD reviewCount: {old.group(0)} -> {REAL_COUNT}")

# 2. Hero badge animated counter: animCounter(r,4.2,1500) - already 4.2, but verify
old = re.search(r'animCounter\(r,([\d.]+),', c)
if old:
    if old.group(1) != REAL_RATING:
        c = c.replace(old.group(0), f'animCounter(r,{REAL_RATING},')
        changes += 1
        print(f"Fixed hero badge: {old.group(1)} -> {REAL_RATING}")
    else:
        print(f"Hero badge already correct: {old.group(1)}")

# 3. Info section: 4.4/5 — 422 avis clients
c, n = re.subn(
    r'(Note Google</h4><p>)[\d.]+/5\s*[—-]\s*\d+\s*avis clients',
    f'\\g<1>{REAL_RATING}/5 — {REAL_COUNT} avis clients',
    c
)
if n: changes += n; print(f"Fixed info section: {n} occurrence(s)")

# 4. Testimonials section: 4.4/5 basé sur <strong>422 avis Google vérifiés</strong>
c, n = re.subn(
    r'[\d.]+/5 basé sur\s*<strong>\d+ avis Google vérifiés</strong>',
    f'{REAL_RATING}/5 basé sur <strong>{REAL_COUNT} avis Google vérifiés</strong>',
    c
)
if n: changes += n; print(f"Fixed testimonials section: {n} occurrence(s)")

# 5. Meta description: notée 4.4/5 sur Google par plus de 520 clients
c, n = re.subn(
    r'notée [\d.]+/5 sur Google par plus de \d+ clients',
    f'notée {REAL_RATING}/5 sur Google par plus de {REAL_COUNT} clients',
    c
)
if n: changes += n; print(f"Fixed meta description: {n} occurrence(s)")

# 6. Also fix "notée <strong>4.4/5 sur Google</strong> par plus de 520 clients"
c, n = re.subn(
    r'notée <strong>[\d.]+/5 sur Google</strong> par plus de \d+ clients',
    f'notée <strong>{REAL_RATING}/5 sur Google</strong> par plus de {REAL_COUNT} clients',
    c
)
if n: changes += n; print(f"Fixed strong meta description: {n} occurrence(s)")

# 7. Review counter target: data-target="422"
# Find the one near "Google" or "AVIS"
old_counter = re.search(r'data-target="(\d+)"\s*Google', c)
if old_counter:
    c = c.replace(old_counter.group(0), f'data-target="{REAL_COUNT}" Google')
    changes += 1
    print(f"Fixed counter target: {old_counter.group(1)} -> {REAL_COUNT}")

# 8. Any other "422 avis" references
c, n = re.subn(r'422 avis', f'{REAL_COUNT} avis', c)
if n: changes += n; print(f"Fixed '422 avis' references: {n} occurrence(s)")

# 9. Any "524 avis" references
c, n = re.subn(r'524 avis', f'{REAL_COUNT} avis', c)
if n: changes += n; print(f"Fixed '524 avis' references: {n} occurrence(s)")

# 10. Any "520 clients" references
c, n = re.subn(r'520 clients', f'{REAL_COUNT} clients', c)
if n: changes += n; print(f"Fixed '520 clients' references: {n} occurrence(s)")

# 11. NOTE GOOGLE /5 text near the badge
c, n = re.subn(r'>[\d.]+</\w+>\s*(<\w+[^>]*>NOTE GOOGLE)', f'>{REAL_RATING}</span> <span class="hero-badge-label">NOTE GOOGLE', c)

print(f"\nTotal changes: {changes}")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done!")
