// Lit le relevé de audit_mobile.js et en tire des constats.
//
//   node .github/scripts/rapport_mobile.js audit-mobile.json
//
// La règle de maison : un constat doit être vrai pour un visiteur, pas
// seulement sortir d'une mesure. Les seuils suivent WCAG 2.2 AA — 4,5:1 pour
// un texte courant, 3:1 pour un grand texte (≥ 24 px, ou ≥ 18,7 px en gras),
// 24 px pour une zone tactile — et tout ce qui n'est pas mesurable de façon
// fiable est compté à part plutôt que présenté comme un défaut.
const fs = require('fs');

const lum = (r, g, b) => {
  const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const ratio = (fg, bg) => {
  const m = String(fg).match(/[\d.]+/g), n = String(bg).match(/[\d.]+/g);
  if (!m || !n) return null;
  const a = m[3] !== undefined ? +m[3] : 1;
  const [br, bgr, bb] = [+n[0], +n[1], +n[2]];
  const fr = a * +m[0] + (1 - a) * br, fg2 = a * +m[1] + (1 - a) * bgr, fb = a * +m[2] + (1 - a) * bb;
  const L1 = lum(fr, fg2, fb), L2 = lum(br, bgr, bb);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
};
const seuil = (px, gras) => (px >= 24 || (gras && px >= 18.66)) ? 3 : 4.5;

const bilan = JSON.parse(fs.readFileSync(process.argv[2] || 'audit-mobile.json', 'utf8'));
const pages = Object.entries(bilan.pages);
const C = {};                                   // constats regroupés
const ajouter = (cle, titre, detail) => {
  C[cle] = C[cle] || { titre, cas: [] };
  C[cle].cas.push(detail);
};

let nbReleves = 0, nonMesurable = 0;
for (const [chemin, etats] of pages) {
  for (const [etat, r] of Object.entries(etats)) {
    nbReleves++;
    const largeur = +etat.split('-')[0].split('×')[0];
    nonMesurable += r.contrasteNonMesurable || 0;

    if (r.largeurMiseEnPage > largeur + 1)
      ajouter('elargissement', 'La page se met en page plus large que l’écran et le navigateur la rétrécit',
        `${chemin} ${etat} : ${r.largeurMiseEnPage} px pour un écran de ${largeur}`);
    if (r.largeurDocument > Math.max(largeur, r.largeurMiseEnPage) + 1)
      ajouter('defilement', 'Défilement horizontal',
        `${chemin} ${etat} : document ${r.largeurDocument} px`);

    for (const o of r.horsEcran || [])
      ajouter('rogne', 'Texte ou commande rogné par le bord de l’écran',
        `${chemin} ${etat} : ${o.q} +${o.px}px « ${o.t} »`);

    for (const o of r.petitTexte || [])
      ajouter('petitTexte', 'Texte sous 12 px, difficile à lire au creux de la main',
        `${chemin} ${etat} : ${o.px}px ${o.q} « ${o.t} »`);

    for (const o of r.contrasteFaible || []) {
      const c = ratio(o.fg, o.bg);
      if (c === null) continue;
      const s = seuil(o.px, o.gras);
      if (c < s)
        ajouter('contraste', 'Contraste sous le minimum lisible',
          `${chemin} ${etat} : ${c.toFixed(2)}:1 (min ${s}) ${o.px}px ${o.q} « ${o.t} »`);
    }

    for (const o of r.ciblesPetites || [])
      ajouter('tactile', 'Zone tactile sous 24 px, serrée contre une autre',
        `${chemin} ${etat} : ${o.w}×${o.h} ${o.q} « ${o.t} »`);

    for (const o of r.masqueFlottant || [])
      ajouter('masque', 'Texte caché sous les boutons flottants en fin de page',
        `${chemin} ${etat} : ${o.q} « ${o.t} »`);

    for (const o of r.motsTropLongs || [])
      ajouter('motLong', 'Texte plus large que son cadre',
        `${chemin} ${etat} : ${o.c} px dans ${o.l} — « ${o.t} »`);

    for (const e of r.erreursJs || [])
      ajouter('js', 'Erreur JavaScript', `${chemin} ${etat} : ${e}`);

    // Viewport : un site qui interdit le zoom bloque les visiteurs qui en ont
    // besoin (WCAG 1.4.4).
    if (r.viewport && /user-scalable\s*=\s*no|maximum-scale\s*=\s*1/.test(r.viewport))
      ajouter('zoom', 'Le zoom est interdit', `${chemin} : ${r.viewport}`);
    if (!r.viewport)
      ajouter('viewport', 'Balise viewport absente', `${chemin}`);
    if (!r.themeColor) ajouter('themeColor', 'Pas de couleur de barre d’adresse (theme-color)', chemin);
    if (!r.toucheIcone) ajouter('icone', 'Pas d’icône d’écran d’accueil (apple-touch-icon)', chemin);

    for (const f of r.champs || []) {
      if (f.px < 16)
        ajouter('zoomSaisie', 'Champ sous 16 px : iOS zoome à la saisie',
          `${chemin} : ${f.id} (${f.px}px)`);
      if (!f.label)
        ajouter('label', 'Champ sans libellé associé', `${chemin} : ${f.id}`);
      if (f.type === 'tel' && !f.inputmode)
        ajouter('clavier', 'Champ téléphone sans inputmode : clavier générique',
          `${chemin} : ${f.id}`);
      if (!f.autocomplete && /prenom|nom|tel|adresse|email/i.test(f.id))
        ajouter('autocomplete', 'Champ sans autocomplete : saisie recommencée à chaque fois',
          `${chemin} : ${f.id}`);
    }

    for (const i of r.images || []) {
      if (i.nat && i.aff && i.nat > i.aff * 2.5)
        ajouter('imageLourde', 'Image chargée bien plus grande qu’affichée',
          `${chemin} : ${i.src} ${i.nat}px pour ${i.aff}px affichés`);
      if (!i.alt) ajouter('alt', 'Image sans texte alternatif', `${chemin} : ${i.src}`);
      if (!i.srcset && i.nat > 900)
        ajouter('srcset', 'Grande image sans variante mobile (srcset)',
          `${chemin} : ${i.src} (${i.nat}px)`);
    }

    if (r.poids) {
      const mo = r.poids.octets / 1048576;
      if (mo > 2.5) ajouter('poids', 'Page lourde pour une connexion mobile',
        `${chemin} : ${mo.toFixed(1)} Mo en ${r.poids.requetes} requêtes`);
    }
    if (r.splash > 3000)
      ajouter('splash', 'Écran d’attente long avant le contenu',
        `${chemin} ${etat} : ${(r.splash / 1000).toFixed(1)} s`);
    if (r.nbNoeuds > 3000)
      ajouter('dom', 'Page très lourde en éléments', `${chemin} : ${r.nbNoeuds} éléments`);
  }
}

// ---------------------------------------------------------------- restitution
const ordre = ['elargissement', 'defilement', 'rogne', 'masque', 'js', 'zoom', 'viewport',
  'contraste', 'petitTexte', 'tactile', 'zoomSaisie', 'label', 'clavier', 'autocomplete',
  'motLong', 'imageLourde', 'srcset', 'alt', 'poids', 'splash', 'dom', 'themeColor', 'icone'];

console.log(`\nAUDIT MOBILE — ${pages.length} pages, ${nbReleves} relevés, ${bilan.duree} s`);
console.log(`Contrastes non mesurables (texte sur photo ou dégradé) : ${nonMesurable}\n`);

let n = 0;
for (const cle of ordre) {
  if (!C[cle]) continue;
  n++;
  const uniques = [...new Set(C[cle].cas)];
  // Combien de pages distinctes sont touchées ?
  const pagesTouchees = new Set(uniques.map(c => c.split(' ')[0]));
  console.log(`${String(n).padStart(2)}. ${C[cle].titre}`);
  console.log(`    ${uniques.length} cas sur ${pagesTouchees.size} page(s)`);
  uniques.slice(0, 6).forEach(c => console.log(`      ${c}`));
  if (uniques.length > 6) console.log(`      … et ${uniques.length - 6} autres`);
  console.log('');
}
if (!n) console.log('Aucun constat.\n');
if (bilan.erreurs.length) {
  console.log('Pages non mesurées :');
  bilan.erreurs.forEach(e => console.log('   ' + e));
}
