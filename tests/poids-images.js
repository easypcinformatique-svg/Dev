// Le poids des images, mesuré comme le vit un téléphone : on charge l'accueil
// sur un écran de 360 px, on le parcourt en entier, et on compte les octets
// réellement reçus.
//
// L'accueil servait 5,0 Mo de photos à un téléphone — des fichiers de 1 400 px
// pour des emplacements de 270. Rien ne le voyait : aucune suite ne regardait
// le poids. Les plafonds ci-dessous sont l'état constaté une fois les versions
// réduites en place, arrondi vers le haut ; ils empêchent le retour en
// arrière, ils ne décrivent pas un idéal.
const { chromium, devices } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';

const PLAFOND_IMAGES = 2.0 * 1048576;   // mesuré : 1,50 Mo
const PLAFOND_TOTAL = 3.0 * 1048576;    // mesuré : 2,41 Mo

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  const ctx = await browser.newContext({
    viewport: { width: 360, height: 740 }, isMobile: true, hasTouch: true,
    deviceScaleFactor: 2, userAgent: devices['iPhone 13'].userAgent });
  const p = await ctx.newPage();
  p.on('dialog', d => d.dismiss());
  const recu = [];
  p.on('response', r => {
    const type = (r.headers()['content-type'] || '').split(';')[0];
    const n = +(r.headers()['content-length'] || 0);
    if (n) recu.push({ u: r.url().split('/').pop(), type, n });
  });

  await p.goto(BASE + '/', { waitUntil: 'load' });
  await p.waitForTimeout(1200);
  // Les images sous la ligne de flottaison ne se chargent qu'au défilement :
  // sans parcourir la page on mesurerait un poids flatteur et faux.
  await p.evaluate(async () => {
    document.documentElement.style.scrollBehavior = 'auto';
    const boite = document.scrollingElement || document.documentElement;
    const haut = Math.max(document.body.scrollHeight, boite.scrollHeight);
    for (let y = 0; y < haut; y += 600) {
      boite.scrollTop = y; document.body.scrollTop = y;
      window.scrollTo({ top: y, behavior: 'instant' });
      await new Promise(r => setTimeout(r, 40));
    }
  });
  await p.waitForTimeout(2500);

  const images = recu.filter(x => /^image/.test(x.type));
  const octetsImg = images.reduce((s, x) => s + x.n, 0);
  const octetsTot = recu.reduce((s, x) => s + x.n, 0);
  const mo = o => (o / 1048576).toFixed(2) + ' Mo';

  t('poids des images sur un téléphone', octetsImg <= PLAFOND_IMAGES,
    `${mo(octetsImg)} en ${images.length} fichiers, plafond ${mo(PLAFOND_IMAGES)}`);
  t('poids total de la page', octetsTot <= PLAFOND_TOTAL,
    `${mo(octetsTot)} en ${recu.length} requêtes, plafond ${mo(PLAFOND_TOTAL)}`);

  const lourdes = images.filter(x => x.n > 200 * 1024).map(x => `${x.u} ${Math.round(x.n / 1024)} ko`);
  t('aucune image au-dessus de 200 ko', lourdes.length === 0, lourdes.slice(0, 4).join(' · '));

  // Chaque balise doit proposer un choix de tailles, sinon le navigateur n'a
  // que la plus grande.
  const sansChoix = await p.evaluate(() => [...document.querySelectorAll('img')]
    .filter(i => i.getBoundingClientRect().width > 0 && i.naturalWidth > 400)
    .filter(i => (i.srcset.match(/\d+w/g) || []).length < 2)
    .map(i => (i.currentSrc || i.src).split('/').pop()));
  t('chaque photo propose plusieurs tailles', sansChoix.length === 0,
    `${sansChoix.length} sans choix : ${sansChoix.slice(0, 4).join(', ')}`);

  // Et la photo du bandeau, qui est un fond CSS : le preload doit suivre
  // l'écran, sinon la pleine taille part quoi qu'en dise la feuille de style.
  const preload = await p.evaluate(() => {
    const l = document.querySelector('link[rel="preload"][as="image"]');
    return l ? { srcset: l.getAttribute('imagesrcset') || '', sizes: l.getAttribute('imagesizes') || '' } : null;
  });
  if (preload) {
    t('le preload du bandeau propose plusieurs tailles',
      (preload.srcset.match(/\d+w/g) || []).length >= 2 && !!preload.sizes,
      `srcset=${preload.srcset.slice(0, 40)} sizes=${preload.sizes}`);
  }

  await ctx.close();
  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
