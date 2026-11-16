// Compatibilité smartphone, mesurée dans un vrai navigateur mobile : débordement
// horizontal, taille des zones tactiles, lisibilité du texte, et le tunnel de
// commande utilisable au pouce. L'audit de septembre excluait ce périmètre.
const { chromium, devices } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';

const PAGES = [
  ['/', 'accueil'],
  ['/livraison-pizza-mazan/', 'page commune'],
  ['/blog/guide-mazan.html', 'guide'],
  ['/pizzeria-carpentras/', 'pizzeria'],
  ['/cgv/', 'CGV'],
];
const ECRANS = [
  { nom: 'iPhone SE', largeur: 375, hauteur: 667 },
  { nom: 'iPhone 14', largeur: 390, hauteur: 844 },
  { nom: 'Android large', largeur: 412, hauteur: 915 },
];

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0, details = [];
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  const mesurer = async (chemin, ecran) => {
    const ctx = await browser.newContext({
      viewport: { width: ecran.largeur, height: ecran.hauteur },
      isMobile: true, hasTouch: true, deviceScaleFactor: 2,
      userAgent: devices['iPhone 13'].userAgent,
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + chemin, { waitUntil: 'load' });
    await p.waitForFunction(() => !document.getElementById('loader') ||
      document.getElementById('loader').classList.contains('hide'), { timeout: 9000 }).catch(() => {});
    await p.waitForTimeout(900);
    const r = await p.evaluate(() => {
      const de = document.documentElement;
      const trop = [];
      // Quels éléments dépassent réellement la largeur de l'écran ?
      for (const e of document.querySelectorAll('body *')) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        if (b.right > window.innerWidth + 1 || b.left < -1) {
          const s = getComputedStyle(e);
          if (s.position === 'fixed' || s.visibility === 'hidden' || s.display === 'none') continue;
          trop.push({ tag: e.tagName.toLowerCase(), cls: (e.className || '').toString().slice(0, 34),
                      debord: Math.round(Math.max(b.right - window.innerWidth, -b.left)) });
        }
      }
      // Zones tactiles trop petites. La norme WCAG 2.5.8 exempte les liens au
      // fil d'une phrase et les cibles masquées : les compter donnerait un
      // chiffre spectaculaire et faux.
      const petites = [];
      for (const e of document.querySelectorAll('a, button, input, select, textarea, [onclick]')) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        if (getComputedStyle(e).display === 'none') continue;
        if (e.classList.contains('skip-link')) continue;          // visible au clavier seulement
        const p = e.parentElement;
        const dansPhrase = p && /^(P|LI|TD|SPAN|STRONG|EM|SMALL)$/.test(p.tagName)
          && p.textContent.trim().length > e.textContent.trim().length + 12;
        if (dansPhrase) continue;
        if (b.height < 24 || b.width < 24) {
          petites.push(`${e.tagName.toLowerCase()}.${(e.className || '').toString().slice(0, 20)} ${Math.round(b.width)}×${Math.round(b.height)}`);
        }
      }
      // Texte trop petit pour être lu sans zoomer
      const minus = [];
      for (const e of document.querySelectorAll('p, li, span, td, label, a')) {
        if (!e.textContent.trim() || e.children.length) continue;
        const px = parseFloat(getComputedStyle(e).fontSize);
        if (px && px < 12) minus.push(`${px.toFixed(1)}px « ${e.textContent.trim().slice(0, 28)} »`);
      }
      return {
        largeurDoc: de.scrollWidth, largeurEcran: window.innerWidth,
        debordements: trop.slice(0, 6), nbDebord: trop.length,
        petites: [...new Set(petites)].slice(0, 6), nbPetites: petites.length,
        minus: [...new Set(minus)].slice(0, 4), nbMinus: minus.length,
        viewport: !!document.querySelector('meta[name="viewport"]'),
      };
    });
    await ctx.close();
    return r;
  };

  for (const ecran of ECRANS) {
    console.log(`\n── ${ecran.nom} (${ecran.largeur} px) ──`);
    for (const [chemin, nom] of PAGES) {
      const r = await mesurer(chemin, ecran);
      const deborde = r.largeurDoc > r.largeurEcran + 1;
      t(`${nom.padEnd(13)} aucun défilement horizontal`, !deborde,
        deborde ? `document ${r.largeurDoc} px pour un écran de ${r.largeurEcran}` : '');
      if (deborde || r.nbDebord) {
        details.push(`${ecran.nom} ${chemin} : ${r.nbDebord} élément(s) hors écran — ` +
          r.debordements.map(d => `${d.tag}.${d.cls} +${d.debord}px`).join(', '));
      }
      if (r.nbPetites) details.push(`${ecran.nom} ${chemin} : ${r.nbPetites} zone(s) tactile(s) < 24px — ${r.petites.join(' · ')}`);
      if (r.nbMinus) details.push(`${ecran.nom} ${chemin} : ${r.nbMinus} texte(s) < 12px — ${r.minus.join(' · ')}`);
      if (ecran === ECRANS[0]) {
        t(`${nom.padEnd(13)} balise viewport présente`, r.viewport);
        // Ces deux-là ne bloquent pas la publication : ce sont des libellés et
        // des liens secondaires, relevés pour qu'ils ne se dégradent pas. Le
        // plafond est l'état constaté le 16/11/2026, pas un idéal.
        const plafondTactile = { 'accueil': 4, 'page commune': 7, 'guide': 18, 'pizzeria': 4, 'CGV': 2 }[nom] ?? 0;
        const plafondTexte = { 'accueil': 21, 'page commune': 8, 'guide': 0, 'pizzeria': 7, 'CGV': 0 }[nom] ?? 0;
        t(`${nom.padEnd(13)} zones tactiles : pas de régression`, r.nbPetites <= plafondTactile,
          `${r.nbPetites} sous 24 px, plafond ${plafondTactile}`);
        t(`${nom.padEnd(13)} petits textes : pas de régression`, r.nbMinus <= plafondTexte,
          `${r.nbMinus} sous 12 px, plafond ${plafondTexte}`);
      }
    }
  }

  // Le tunnel de commande au pouce
  console.log('\n── tunnel de commande sur iPhone SE ──');
  {
    const ctx = await browser.newContext({
      viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true,
      deviceScaleFactor: 2, userAgent: devices['iPhone 13'].userAgent });
    await ctx.addInitScript(() => {
      const R = Date, f = new R('2026-11-16T14:00:00');
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + '/', { waitUntil: 'load' });
    await p.waitForFunction(() => document.getElementById('loader')?.classList.contains('hide'), { timeout: 9000 });
    await p.waitForTimeout(700);
    await p.evaluate(() => openCommander());
    await p.waitForTimeout(400);
    await p.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await p.waitForTimeout(300);
    t('le formulaire s’ouvre', await p.locator('#order-overlay.open').count() > 0);
    const champ = await p.locator('#client-prenom').boundingBox();
    t('les champs tiennent dans l’écran', champ && champ.x >= 0 && champ.x + champ.width <= 376,
      champ ? `x=${Math.round(champ.x)} largeur=${Math.round(champ.width)}` : 'champ absent');
    const taille = await p.evaluate(() => parseFloat(getComputedStyle(document.getElementById('client-tel')).fontSize));
    // En dessous de 16 px, iOS zoome automatiquement à la saisie.
    t('saisie sans zoom automatique iOS (≥16 px)', taille >= 16, `${taille}px`);
    const dep = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    t('formulaire sans débordement', dep <= 1, `${dep}px`);
    await ctx.close();
  }

  if (details.length) {
    console.log('\n── détail des écarts ──');
    [...new Set(details)].slice(0, 14).forEach(d => console.log('   ' + d));
  }
  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
