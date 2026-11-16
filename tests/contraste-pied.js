// Le bloc de liens par commune, en bas de page, s'affichait en blanc sur
// blanc : un contraste de 1,00:1, invisible sur tous les écrans depuis des
// mois. Cause : c'est un <nav>, et la feuille du site habille « nav » sans
// classe, fond blanc de l'en-tête compris. Rien dans les treize suites
// existantes ne regardait une couleur — elles vérifiaient des textes, des
// liens, des tailles. Celle-ci mesure le contraste réel de chaque texte du
// pied de page, sur chaque page, et refuse la publication sous 4,5:1.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';
const SITE = process.env.SITE_DIR || '';
const SEUIL = 4.5;   // WCAG 2.2 AA, texte normal

// Pages de secours si le dossier du site n'est pas fourni : une par famille
// de pied de page (accueil, commune, pizzeria, guide, CGV).
const SECOURS = ['index.html', 'livraison-pizza-mazan/index.html',
  'pizzeria-carpentras/index.html', 'blog/guide-mazan.html', 'cgv/index.html'];

const lister = (dir, base = dir) => fs.readdirSync(dir, { withFileTypes: true })
  .flatMap(e => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return e.name === '.git' ? [] : lister(p, base);
    return e.name.endsWith('.html') ? [path.relative(base, p)] : [];
  });

const luminance = (r, g, b) => {
  const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};

const contraste = (fg, bg) => {
  const m = fg.match(/[\d.]+/g), n = bg.match(/[\d.]+/g);
  if (!m || !n) return null;
  const a = m[3] !== undefined ? +m[3] : 1;
  const [br, bgr, bb] = [+n[0], +n[1], +n[2]];
  // Un texte semi-transparent se lit par-dessus son fond : on compose.
  const fr = a * +m[0] + (1 - a) * br, fgr = a * +m[1] + (1 - a) * bgr, fb = a * +m[2] + (1 - a) * bb;
  const L1 = luminance(fr, fgr, fb), L2 = luminance(br, bgr, bb);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
};

(async () => {
  const pages = SITE && fs.existsSync(SITE) ? lister(SITE).sort() : SECOURS;
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({
    viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, userAgent: devices['iPhone 13'].userAgent });
  const p = await ctx.newPage();
  p.on('dialog', d => d.dismiss());

  let pire = { r: 99 }, fautes = [], vues = 0;
  for (const f of pages) {
    await p.goto(BASE + '/' + f, { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(300);
    // On ne retient que les textes posés sur une couleur unie : au-dessus
    // d'une photo ou d'un dégradé, le rapport calculé ne voudrait rien dire.
    const textes = await p.evaluate(() => {
      const fond = e => {
        let x = e;
        while (x) {
          const s = getComputedStyle(x);
          if (s.backgroundImage && s.backgroundImage !== 'none') return null;
          const c = s.backgroundColor;
          if (c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c;
          x = x.parentElement;
        }
        return 'rgb(255, 255, 255)';
      };
      const out = [];
      for (const e of document.querySelectorAll('footer, footer *')) {
        if (e.children.length || !e.textContent.trim()) continue;
        const s = getComputedStyle(e);
        if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
        const b = fond(e);
        if (!b) continue;
        out.push({ t: e.textContent.trim().slice(0, 34), fg: s.color, bg: b, px: s.fontSize });
      }
      return out;
    });
    vues += textes.length;
    for (const o of textes) {
      const r = contraste(o.fg, o.bg);
      if (r === null) continue;
      if (r < pire.r) pire = { r, ...o, page: f };
      if (r < SEUIL) fautes.push(`${f} — ${r.toFixed(2)}:1 à ${o.px} « ${o.t} »`);
    }
  }
  await ctx.close();
  await browser.close();

  console.log(`  ${pages.length} page(s), ${vues} texte(s) de pied de page mesuré(s)`);
  if (pire.r < 99) {
    console.log(`  le plus faible : ${pire.r.toFixed(2)}:1 — ${pire.page} « ${pire.t} »`);
  }
  if (fautes.length) {
    console.log(`\n  ECHEC ${fautes.length} texte(s) sous ${SEUIL}:1`);
    [...new Set(fautes)].slice(0, 12).forEach(l => console.log('   ' + l));
    process.exit(1);
  }
  console.log(`\n  tout le pied de page est au-dessus de ${SEUIL}:1`);
})();
