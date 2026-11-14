// Liens internes et ancres, vérifiés sur les fichiers avant toute publication.
// Pas besoin de navigateur : une ancre morte ou un lien vers une page absente
// se voient dans le HTML. C'est ce contrôle qui manquait quand sept guides
// renvoyaient vers des sections inexistantes.
const fs = require('fs');
const path = require('path');

const SITE = process.env.SITE_DIR || process.argv[2];
if (!SITE) { console.error('usage : node tests/liens-internes.js <dossier du site>'); process.exit(2); }

const fichiers = [];
(function parcourir(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) parcourir(p);
    else if (e.name.endsWith('.html')) fichiers.push(p);
  }
})(SITE);

const existe = rel => {
  const p = path.join(SITE, rel.replace(/^\//, ''));
  if (fs.existsSync(p) && fs.statSync(p).isFile()) return true;
  return fs.existsSync(path.join(p, 'index.html'));
};

const mortes = [], absentes = [];
for (const f of fichiers) {
  const c = fs.readFileSync(f, 'utf8');
  const rel = path.relative(SITE, f);
  const ids = new Set([...c.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]));
  for (const m of c.matchAll(/href="([^"]+)"/g)) {
    const href = m[1];
    if (/^(mailto:|tel:|javascript:|data:|https?:)/.test(href)) continue;
    const [chemin, ancre] = href.split('#');
    if (!chemin && ancre && !ids.has(ancre)) { mortes.push(`${rel} → #${ancre}`); continue; }
    if (!chemin) continue;
    // Les liens absolus du site pointent vers la racine du dossier servi.
    const cible = chemin.startsWith('/') ? chemin : path.join('/', path.dirname(rel), chemin);
    if (!existe(cible)) absentes.push(`${rel} → ${chemin}`);
  }
}

let ok = 0, total = 0;
const t = (nom, cond, detail = []) => {
  total++; if (cond) ok++;
  console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}`);
  if (!cond) detail.slice(0, 10).forEach(d => console.log(`         ${d}`));
};

console.log(`  ${fichiers.length} pages examinées`);
t('aucune ancre ne pointe dans le vide', mortes.length === 0, mortes);
t('aucun lien interne vers une page absente', absentes.length === 0, absentes);

console.log(`\n  ${ok}/${total} conformes`);
process.exit(ok === total ? 0 : 1);
