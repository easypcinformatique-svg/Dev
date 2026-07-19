import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "site/index.html"

with open(path, "r", encoding="utf-8") as f:
    c = f.read()

changes = []

# 1. Fix time slots: remove before 19h30 and after 21h30
slots_to_remove = [
    '<option value="18h00">18h00</option>',
    '<option value="18h15">18h15</option>',
    '<option value="18h30">18h30</option>',
    '<option value="18h45">18h45</option>',
    '<option value="19h00">19h00</option>',
    '<option value="19h15">19h15</option>',
    '<option value="21h45">21h45</option>',
]
for slot in slots_to_remove:
    if slot in c:
        c = c.replace(slot, '')
        changes.append('Removed slot: ' + slot.split('>')[1].split('<')[0])

# 2. Add Monteux to zone table (after Serres row)
if 'Monteux' not in c.split('Minimum de commande')[1].split('</table>')[0] if 'Minimum de commande' in c else '':
    monteux_row = '<tr style="border-bottom:1px solid rgba(255,255,255,.07);"> <td style="padding:.55rem 1rem;">\U0001f4cd Monteux</td> <td style="text-align:center;padding:.55rem 1rem;">3 grandes pizzas</td> </tr>'
    # Insert after Serres row
    serres_end = c.find('Serres</td>')
    if serres_end > 0:
        # Find end of Serres row
        tr_end = c.find('</tr>', serres_end)
        if tr_end > 0:
            insert_pos = tr_end + 5
            c = c[:insert_pos] + ' ' + monteux_row + c[insert_pos:]
            changes.append('Added Monteux to zone table (3 grandes pizzas)')

# 3. Add zone validation JS
# Find the envoyerWhatsApp function or form submit and add validation before it
validation_js = """
// Zone minimum validation
function getMinPizzasForCity(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1 || a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1) return 4;
  if (a.indexOf('pernes') !== -1 || a.indexOf('aubignan') !== -1 || a.indexOf('loriol') !== -1 || a.indexOf('caromb') !== -1 || a.indexOf('monteux') !== -1) return 3;
  if (a.indexOf('carpentras') !== -1 || a.indexOf('serres') !== -1 || a.indexOf('84200') !== -1) return 2;
  return 2;
}

function getCityName(addr) {
  var a = addr.toLowerCase();
  if (a.indexOf('mazan') !== -1) return 'Mazan';
  if (a.indexOf('saint-didier') !== -1 || a.indexOf('st-didier') !== -1 || a.indexOf('st didier') !== -1) return 'Saint-Didier';
  if (a.indexOf('pernes') !== -1) return 'Pernes-les-Fontaines';
  if (a.indexOf('aubignan') !== -1) return 'Aubignan';
  if (a.indexOf('loriol') !== -1) return 'Loriol-du-Comtat';
  if (a.indexOf('caromb') !== -1) return 'Caromb';
  if (a.indexOf('monteux') !== -1) return 'Monteux';
  if (a.indexOf('serres') !== -1) return 'Serres';
  if (a.indexOf('carpentras') !== -1 || a.indexOf('84200') !== -1) return 'Carpentras';
  return '';
}

// Free bottle offer: 1 per order when 3+ pizzas
var freeBottleChosen = false;
var originalEnvoyerWhatsApp = typeof envoyerWhatsApp === 'function' ? envoyerWhatsApp : null;
"""

if 'getMinPizzasForCity' not in c:
    # Insert before closing </script> or </body>
    insert_marker = '</body>'
    c = c.replace(insert_marker, '<script>' + validation_js + '</script>\n' + insert_marker)
    changes.append('Added zone minimum validation JS')

# 4. Add free bottle popup HTML
bottle_popup = """
<div id="free-bottle-popup" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:10000;align-items:center;justify-content:center;">
<div style="background:#FFFDF7;border-radius:12px;padding:2rem;max-width:380px;text-align:center;margin:1rem;">
<h3 style="color:#c0392b;font-size:1.3rem;margin-bottom:.5rem;">\U0001f381 Boisson offerte !</h3>
<p style="color:#555;font-size:.9rem;margin-bottom:1.2rem;">3 pizzas achetees = 1 bouteille 1.5L offerte.<br>Choisissez votre boisson :</p>
<div style="display:flex;flex-direction:column;gap:.6rem;">
<button onclick="selectFreeBottle('Coca-Cola 1.5L')" style="padding:.8rem;border:2px solid #c0392b;background:white;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600;">Coca-Cola 1.5L</button>
<button onclick="selectFreeBottle('Fanta 1.5L')" style="padding:.8rem;border:2px solid #f39c12;background:white;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600;">Fanta 1.5L</button>
<button onclick="selectFreeBottle('Ice Tea 1.5L')" style="padding:.8rem;border:2px solid #27ae60;background:white;border-radius:8px;font-size:1rem;cursor:pointer;font-weight:600;">Ice Tea 1.5L</button>
</div>
<p style="color:#999;font-size:.75rem;margin-top:.8rem;">1 bouteille offerte par commande</p>
</div>
</div>
"""

bottle_js = """
<script>
var selectedFreeBottle = '';
function selectFreeBottle(name) {
  selectedFreeBottle = name;
  document.getElementById('free-bottle-popup').style.display = 'none';
  // Show confirmation
  var conf = document.createElement('div');
  conf.style.cssText = 'position:fixed;top:1rem;left:50%;transform:translateX(-50%);background:#27ae60;color:white;padding:.8rem 1.5rem;border-radius:8px;font-weight:600;z-index:10001;font-size:.9rem;';
  conf.textContent = '\\u2705 ' + name + ' offerte ajoutee !';
  document.body.appendChild(conf);
  setTimeout(function(){conf.remove();}, 3000);
}

// Override nextStep to check zone minimum and show bottle offer
var _origNextStep = typeof nextStep === 'function' ? nextStep : null;
if (_origNextStep) {
  nextStep = function(step) {
    // When moving from step 2 (pizzas) to step 3 (drinks)
    if (step === 2) {
      // Count total pizzas
      var totalPizzas = 0;
      var qtyEls = document.querySelectorAll('.qty-value');
      qtyEls.forEach(function(el) { totalPizzas += parseInt(el.textContent) || 0; });

      // Show free bottle popup if 3+ pizzas and not already chosen
      if (totalPizzas >= 3 && !selectedFreeBottle) {
        document.getElementById('free-bottle-popup').style.display = 'flex';
      }
    }
    // When moving from step 3 to step 4 (info)
    if (step === 3) {
      // Zone validation will happen at final submit
    }
    _origNextStep(step);
  };
}

// Override envoyerWhatsApp to validate zone minimum
var _origEnvoyer = typeof envoyerWhatsApp === 'function' ? envoyerWhatsApp : null;
if (_origEnvoyer) {
  envoyerWhatsApp = function() {
    var addr = '';
    var addrEl = document.getElementById('client-adresse');
    if (addrEl) addr = addrEl.value;

    var modeLivraison = document.getElementById('mode-livraison');
    var isLivraison = modeLivraison && modeLivraison.classList.contains('active');

    if (isLivraison && addr) {
      var minPizzas = getMinPizzasForCity(addr);
      var cityName = getCityName(addr);

      // Count total pizzas
      var totalPizzas = 0;
      var qtyEls = document.querySelectorAll('.qty-value');
      qtyEls.forEach(function(el) { totalPizzas += parseInt(el.textContent) || 0; });

      if (totalPizzas < minPizzas && cityName) {
        alert('Minimum ' + minPizzas + ' grandes pizzas pour la livraison a ' + cityName + '.\\nVous avez ' + totalPizzas + ' pizza(s). Ajoutez-en pour commander.');
        return;
      }
    }

    // Add free bottle to message if selected
    if (selectedFreeBottle && typeof window._whatsappMsg !== 'undefined') {
      window._whatsappMsg += '\\n\\U0001f381 Boisson offerte : ' + selectedFreeBottle;
    }

    _origEnvoyer();
  };
}
</script>
"""

if 'free-bottle-popup' not in c:
    c = c.replace('</body>', bottle_popup + bottle_js + '\n</body>')
    changes.append('Added free bottle popup (1 per order, 3+ pizzas)')
    changes.append('Added zone minimum validation on submit')

print(f'Total changes: {len(changes)}')
for ch in changes:
    print(f'  - {ch}')

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
