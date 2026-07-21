import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Replace old validation that defaults to 2
old_validation = """function getMinPizzasForCity(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1 || a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1) return 4;
  if (a.indexOf('pernes') !== -1 || a.indexOf('aubignan') !== -1 || a.indexOf('loriol') !== -1 || a.indexOf('caromb') !== -1 || a.indexOf('monteux') !== -1) return 3;
  if (a.indexOf('carpentras') !== -1 || a.indexOf('serres') !== -1 || a.indexOf('84200') !== -1) return 2;
  return 2;
}"""

# New validation: return -1 if city not in zone (will block the order)
new_validation = """function getMinPizzasForCity(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1 || a.indexOf('84380') !== -1) return 4;
  if (a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1 || a.indexOf('84210') !== -1) return 4;
  if (a.indexOf('pernes') !== -1) return 3;
  if (a.indexOf('aubignan') !== -1 || a.indexOf('84810') !== -1) return 3;
  if (a.indexOf('loriol') !== -1 || a.indexOf('84870') !== -1) return 3;
  if (a.indexOf('caromb') !== -1 || a.indexOf('84330') !== -1) return 3;
  if (a.indexOf('monteux') !== -1 || a.indexOf('84170') !== -1) return 3;
  if (a.indexOf('carpentras') !== -1 || a.indexOf('84200') !== -1) return 2;
  if (a.indexOf('serres') !== -1) return 2;
  return -1;
}"""

if old_validation in c:
    c = c.replace(old_validation, new_validation)
    print("Replaced zone validation: unknown cities now return -1 (blocked)")
else:
    print("WARNING: old validation not found, trying partial match")
    # Try replacing just the return 2; at the end
    c = c.replace("  if (a.indexOf('carpentras') !== -1 || a.indexOf('serres') !== -1 || a.indexOf('84200') !== -1) return 2;\n  return 2;\n}",
                   "  if (a.indexOf('carpentras') !== -1 || a.indexOf('84200') !== -1) return 2;\n  if (a.indexOf('serres') !== -1) return 2;\n  return -1;\n}")
    print("Partial fix applied")

# Also update getCityName to return empty for unknown cities (already does)
# And update the validation in envoyerWhatsApp to handle -1

old_check = """      if (totalPoints < minPizzas && cityName) {"""
new_check = """      if (minPizzas === -1) {
        alert('Desole, nous ne livrons pas a cette adresse.\\nNous livrons uniquement a : Carpentras, Serres, Pernes-les-Fontaines, Aubignan, Loriol-du-Comtat, Caromb, Monteux, Mazan, Saint-Didier.\\nVerifiez votre adresse ou choisissez A emporter.');
        return;
      }
      if (totalPoints < minPizzas && cityName) {"""

if old_check in c:
    c = c.replace(old_check, new_check, 1)
    print("Added block for unknown cities in envoyerWhatsApp")
else:
    print("WARNING: could not find check block to add city validation")

# Also add the same check in the nextStep override if it exists
old_next_check = """      // Show free bottle popup if 3+ pizzas and not already chosen"""
new_next_check = """      // Check zone before proceeding
      var addrEl2 = document.getElementById('client-adresse');
      var modeLiv = document.getElementById('mode-livraison');
      if (addrEl2 && modeLiv && modeLiv.classList && modeLiv.classList.contains('active')) {
        var addr2 = addrEl2.value;
        if (addr2 && getMinPizzasForCity(addr2) === -1) {
          alert('Desole, nous ne livrons pas a cette adresse.\\nVilles desservies : Carpentras, Serres, Pernes, Aubignan, Loriol, Caromb, Monteux, Mazan, Saint-Didier.');
          return;
        }
      }
      // Show free bottle popup if 3+ pizzas and not already chosen"""

if old_next_check in c:
    c = c.replace(old_next_check, new_next_check, 1)
    print("Added zone check in nextStep override")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done!")
