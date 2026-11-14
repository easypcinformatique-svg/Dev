// Le minimum de commande est écrit de six façons différentes sur le site :
// tableaux, prose, meta description, og:description. Plutôt que de vérifier
// chaque formulation, on apparie chaque nombre de pizzas à la commune la plus
// proche qui le précède, et on exige l'accord. C'est ce contrôle qui manquait
// quand Pernes-les-Fontaines est resté à 3 pendant que tout le reste passait à 5.
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SITE = process.env.SITE_DIR || process.argv[2];
if (!SITE) { console.error('usage : node tests/minimums.js <dossier du site>'); process.exit(2); }

const guard = fs.readFileSync(path.join(__dirname, '..', '.github', 'scripts', 'site_guard.py'), 'utf8');
const table = guard.match(/COMMUNES = \{([\s\S]*?)\n\}/)[1];
const MINI = {};
for (const m of table.matchAll(/"[^"]+":\s*\("([^"]+)",\s*"\d+",\s*(\d+)/g)) MINI[m[1]] = +m[2];

const villes = Object.keys(MINI).sort((a, b) => b.length - a.length);
const rv = new RegExp(villes.map(v => v.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|'), 'g');
const rn = /(\d+)\s*(grandes?|petites?)\b/g;
const marque = /(Pizza )?Napoli\s*$/i;

const fichiers = [];
(function parcourir(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) parcourir(p);
    else if (e.name.endsWith('.html')) fichiers.push(p);
  }
})(SITE);

let desaccords = [];
for (const f of fichiers) {
  const c = fs.readFileSync(f, 'utf8');
  const reperes = [...c.matchAll(rv)].map(m => [m.index + m[0].length, m[0]]);
  for (const m of c.matchAll(rn)) {
    const avant = reperes.filter(v => v[0] <= m.index);
    if (!avant.length) continue;
    const [fin, ville] = avant[avant.length - 1];
    const ecart = m.index - fin;
    if (ecart > 90) continue;
    if (/<\/tr>|<\/li>|<\/ul>|📍/.test(c.slice(fin, m.index))) continue;
    if (marque.test(c.slice(Math.max(0, fin - ville.length - 14), fin - ville.length))) continue;
    const attendu = MINI[ville] * (m[2].startsWith('petite') ? 2 : 1);
    if (+m[1] !== attendu) {
      desaccords.push(`${path.relative(SITE, f)} — ${ville} : « ${m[0]} », attendu ${attendu}`);
    }
  }
}

console.log(`  ${fichiers.length} pages examinées, ${Object.keys(MINI).length} communes`);
desaccords.slice(0, 15).forEach(d => console.log(`  ECHEC ${d}`));
const ok = desaccords.length === 0;
console.log(`  ${ok ? 'OK   ' : 'ECHEC'} aucun minimum en désaccord avec la commune citée`);
console.log(`\n  ${ok ? 1 : 0}/1 conformes`);
process.exit(ok ? 0 : 1);
