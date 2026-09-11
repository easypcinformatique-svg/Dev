import re, sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

changes = 0

# Fix the broken counter HTML: data-target="422" Google</span>
# Should be: data-target="526">0</span><span class="counter-lbl">Avis Google</span>
broken = re.search(r'<span class="counter-num" data-target="\d+"[^>]*Google</span>', c)
if broken:
    fixed = '<span class="counter-num" data-target="526">0</span><span class="counter-lbl">Avis Google</span>'
    c = c.replace(broken.group(0), fixed)
    changes += 1
    print(f"Fixed broken counter: {broken.group(0)[:60]}... -> proper HTML with 526")

# Also replace any remaining "422" that's near avis/Google context
old_pattern = re.search(r'data-target="422"', c)
if old_pattern:
    c = c.replace('data-target="422"', 'data-target="526"')
    changes += 1
    print("Fixed data-target 422 -> 526")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print(f"Changes: {changes}")
