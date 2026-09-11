import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# Remove old injection if present
if "/* === ZONE VALIDATION === */" in c:
    # Remove everything between ZONE VALIDATION markers
    c = re.sub(r'/\* === ZONE VALIDATION === \*/.*?/\* === FIN ZONE VALIDATION === \*/', '', c, flags=re.DOTALL)
    print("Removed old zone validation injection")

# Find the original envoyerWhatsApp function start
original_start = "function envoyerWhatsApp() {"

# New validation using pizzaOrders (the actual data structure)
validation_code = """function envoyerWhatsApp() {
/* === ZONE VALIDATION === */
var _modeCheck = document.querySelector('input[name="mode"]:checked');
if (_modeCheck && _modeCheck.value === 'livraison') {
  var _addr = document.getElementById('client-adresse') ? document.getElementById('client-adresse').value : '';
  if (_addr) {
    var _a = _addr.toLowerCase();
    var _min = -1;
    if (_a.indexOf('mazan') !== -1 || _a.indexOf('84380') !== -1) _min = 4;
    else if (_a.indexOf('saint-didier') !== -1 || _a.indexOf('st-didier') !== -1 || _a.indexOf('st didier') !== -1 || _a.indexOf('84210') !== -1) _min = 4;
    else if (_a.indexOf('pernes') !== -1 && _a.indexOf('pennes') === -1) _min = 3;
    else if (_a.indexOf('aubignan') !== -1 || _a.indexOf('84810') !== -1) _min = 3;
    else if (_a.indexOf('loriol') !== -1 || _a.indexOf('84870') !== -1) _min = 3;
    else if (_a.indexOf('caromb') !== -1 || _a.indexOf('84330') !== -1) _min = 3;
    else if (_a.indexOf('monteux') !== -1 || _a.indexOf('84170') !== -1) _min = 3;
    else if (_a.indexOf('carpentras') !== -1 || _a.indexOf('84200') !== -1) _min = 2;
    else if (_a.indexOf('serres') !== -1) _min = 2;
    if (_min === -1) {
      alert('Desole, nous ne livrons pas a cette adresse.\\nNous livrons uniquement a : Carpentras, Serres, Pernes-les-Fontaines, Aubignan, Loriol-du-Comtat, Caromb, Monteux, Mazan, Saint-Didier.\\nVerifiez votre adresse ou choisissez A emporter.');
      return;
    }
    var _totalPts = 0;
    if (typeof pizzaOrders !== 'undefined') {
      Object.values(pizzaOrders).forEach(function(o) {
        if (o.qty > 0) {
          _totalPts += o.qty * (o.size === '26' ? 0.5 : 1);
        }
      });
    }
    if (_totalPts < _min) {
      alert('Minimum pour livrer a cette adresse : ' + _min + ' grandes pizzas (ou ' + (_min*2) + ' petites).\\nVotre commande equivaut a ' + _totalPts + ' grande(s).\\nAjoutez des pizzas pour commander en livraison.');
      return;
    }
  }
}
/* === FIN ZONE VALIDATION === */"""

if original_start in c:
    c = c.replace(original_start, validation_code, 1)
    print("Injected zone validation using pizzaOrders (size 26=petite)")
else:
    print("WARNING: could not find envoyerWhatsApp function")

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Done!")
