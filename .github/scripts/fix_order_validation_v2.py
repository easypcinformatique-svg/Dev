import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

changes = []

# 1. Replace old zone validation JS with new one that counts grande=1, petite=0.5
old_validation = """// Zone minimum validation
function getMinPizzasForCity(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1 || a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1) return 4;
  if (a.indexOf('pernes') !== -1 || a.indexOf('aubignan') !== -1 || a.indexOf('loriol') !== -1 || a.indexOf('caromb') !== -1 || a.indexOf('monteux') !== -1) return 3;
  if (a.indexOf('carpentras') !== -1 || a.indexOf('serres') !== -1 || a.indexOf('84200') !== -1) return 2;
  return 2;
}"""

new_validation = """// Zone minimum validation (1 grande = 1pt, 1 petite = 0.5pt)
function getMinPizzasForCity(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1 || a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1) return 4;
  if (a.indexOf('pernes') !== -1 || a.indexOf('aubignan') !== -1 || a.indexOf('loriol') !== -1 || a.indexOf('caromb') !== -1 || a.indexOf('monteux') !== -1) return 3;
  if (a.indexOf('carpentras') !== -1 || a.indexOf('serres') !== -1 || a.indexOf('84200') !== -1) return 2;
  return 2;
}
function getMinPizzasText(min) {
  return min + ' grandes pizzas (ou ' + (min * 2) + ' petites)';
}"""

if old_validation in c:
    c = c.replace(old_validation, new_validation)
    changes.append("Updated zone validation with grande/petite text")

# 2. Replace the old alert validation that just counts qty with new one that counts points
# Find the validation block in envoyerWhatsApp override
old_count = """      // Count total pizzas
      var totalPizzas = 0;
      var qtyEls = document.querySelectorAll('.qty-value');
      qtyEls.forEach(function(el) { totalPizzas += parseInt(el.textContent) || 0; });

      if (totalPizzas < minPizzas && cityName) {
        alert('Minimum ' + minPizzas + ' grandes pizzas pour la livraison a ' + cityName + '.\\nVous avez ' + totalPizzas + ' pizza(s). Ajoutez-en pour commander.');
        return;
      }"""

new_count = """      // Count pizza points: grande = 1pt, petite = 0.5pt
      var totalPoints = 0;
      var allCards = document.querySelectorAll('.pizza-card, .drink-card, [data-pizza]');
      var qtyEls = document.querySelectorAll('.qty-value');
      qtyEls.forEach(function(el, idx) {
        var qty = parseInt(el.textContent) || 0;
        if (qty > 0) {
          var card = el.closest('.pizza-card, [data-pizza], .menu-item');
          var isGrande = true;
          if (card) {
            var sizeEl = card.querySelector('.size-selected, .size-active, [data-size]');
            var text = card.textContent.toLowerCase();
            if (text.indexOf('petite') !== -1 && text.indexOf('grande') === -1) isGrande = false;
            if (sizeEl && sizeEl.textContent.toLowerCase().indexOf('petite') !== -1) isGrande = false;
          }
          totalPoints += qty * (isGrande ? 1 : 0.5);
        }
      });

      if (totalPoints < minPizzas && cityName) {
        alert('Minimum pour la livraison a ' + cityName + ' : ' + minPizzas + ' grandes pizzas (ou ' + (minPizzas * 2) + ' petites).\\nVotre commande equivaut a ' + totalPoints + ' grande(s). Ajoutez des pizzas pour commander.');
        return;
      }"""

if old_count in c:
    c = c.replace(old_count, new_count)
    changes.append("Updated validation to count grande=1pt, petite=0.5pt")
else:
    # Try simpler replacement - find the alert line
    old_alert = "alert('Minimum ' + minPizzas + ' grandes pizzas"
    if old_alert in c:
        # Replace the whole validation block more broadly
        idx = c.find("// Count total pizzas")
        if idx > 0:
            end = c.find("return;", idx)
            if end > 0:
                end = c.find("\n", end) + 1
                old_block = c[idx:end]
                c = c[:idx] + new_count.strip() + c[end:]
                changes.append("Replaced validation block (broad match)")

# 3. Update the zone table to show "ou X petites"
zone_replacements = [
    ("2 grandes pizzas</td>", "2 grandes (ou 4 petites)</td>"),
    ("3 grandes pizzas</td>", "3 grandes (ou 6 petites)</td>"),
    ("4 grandes pizzas</td>", "4 grandes (ou 8 petites)</td>"),
]
for old, new in zone_replacements:
    if old in c:
        c = c.replace(old, new)
        changes.append("Updated zone table: " + old[:30])

# 4. Fix font-display:swap
if "font-display:swap" not in c and "font-display" not in c:
    c = c.replace("@font-face{", "@font-face{font-display:swap;")
    changes.append("Added font-display:swap")

# 5. Add BreadcrumbList to homepage
if "BreadcrumbList" not in c:
    breadcrumb = '<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"Pizza Napoli Carpentras","item":"https://pizzanapolicarpentras.fr/"}]}</script>'
    c = c.replace("</head>", breadcrumb + "\n</head>", 1)
    changes.append("Added BreadcrumbList to homepage")

print(f"Total changes: {len(changes)}")
for ch in changes:
    print(f"  - {ch}")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
