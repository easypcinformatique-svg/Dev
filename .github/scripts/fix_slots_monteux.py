import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1. Remove 21h45 slot (multiple formats)
c = c.replace('<option value="21h45">21h45</option>', '')
c = c.replace('<option value="21h45">21h45 — dernier créneau</option>', '')
c = c.replace('<option value="21h45">21h45 &mdash; dernier cr&eacute;neau</option>', '')
# Make 21h30 the last slot with "dernier creneau" label
c = c.replace('<option value="21h30">21h30</option>', '<option value="21h30">21h30 — dernier créneau</option>')
print("Removed 21h45 slot, 21h30 is now dernier creneau")

# 2. Add Monteux to zone table before Mazan row
monteux_row = '<tr style="border-bottom:1px solid rgba(255,255,255,.07);"> <td style="padding:.55rem 1rem;">\U0001f4cd Monteux</td> <td style="text-align:center;padding:.55rem 1rem;">3 grandes pizzas</td> </tr>'

if 'Monteux</td>' not in c.split('Minimum de commande')[1].split('</table>')[0] if 'Minimum de commande' in c else True:
    # Insert before Mazan row
    mazan_marker = '\U0001f4cd Mazan</td>'
    idx = c.find(mazan_marker)
    if idx > 0:
        # Find the <tr that starts this row
        tr_start = c.rfind('<tr', 0, idx)
        if tr_start > 0:
            c = c[:tr_start] + monteux_row + ' ' + c[tr_start:]
            print("Added Monteux to zone table (before Mazan)")
    else:
        print("WARNING: Could not find Mazan row to insert Monteux")
else:
    print("Monteux already in zone table")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

# Also ensure 21h45 is removed (may have been re-added)
if '<option value="21h45">21h45</option>' in c:
    c = c.replace('<option value="21h45">21h45</option>', '')
    print("Removed 21h45 slot (cleanup)")
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)

print("Done!")
