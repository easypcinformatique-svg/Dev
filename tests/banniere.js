// La bannière : le texte doit rester lisible sur la photo, quelle que soit la
// photo. On mesure le fond réellement rendu derrière le sous-titre plutôt que
// de faire confiance à la valeur du dégradé.
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';
const { PNG } = (() => { try { return { PNG: require('pngjs').PNG }; } catch (e) { return {}; } })();

const canal = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
const lum = (r, g, b) => 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b);

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 820 } });
  const page = await ctx.newPage();
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  await page.goto(BASE + '/', { waitUntil: 'load' });
  await page.waitForSelector('#loader.hide', { timeout: 10000 });
  await page.waitForTimeout(1200);

  const fond = await page.evaluate(() => getComputedStyle(document.querySelector('.hero')).backgroundImage);
  t('la bannière porte une photo', /url\(/.test(fond), fond.slice(0, 80));
  t('la photo de bannière se charge', await page.evaluate(async () => {
    const u = getComputedStyle(document.querySelector('.hero')).backgroundImage.match(/url\("?([^")]+)"?\)/);
    if (!u) return false;
    const r = await fetch(u[1], { method: 'HEAD' });
    return r.ok;
  }), fond.match(/url\("?([^")]+)/) ? fond.match(/url\("?([^")]+)/)[1] : '');

  const sous = page.locator('.hero-sub').last();
  const boite = await sous.boundingBox();
  t('le sous-titre est visible', boite && boite.height > 0);

  // On masque les textes pour photographier uniquement ce qu'il y a derrière.
  await page.evaluate(() => document.querySelectorAll('.hero-sub,.hero-title,.hero-badge,.hero-btns')
    .forEach(e => (e.style.visibility = 'hidden')));
  await page.waitForTimeout(200);
  const png = await page.screenshot({ clip: boite });

  // Décodage PNG sans dépendance : on passe par le canvas de la page.
  const pires = await page.evaluate(async (data) => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + data;
    await img.decode();
    const cv = document.createElement('canvas');
    cv.width = img.width; cv.height = img.height;
    cv.getContext('2d').drawImage(img, 0, 0);
    const d = cv.getContext('2d').getImageData(0, 0, cv.width, cv.height).data;
    const px = [];
    for (let i = 0; i < d.length; i += 4) px.push([d[i], d[i + 1], d[i + 2]]);
    return px;
  }, png.toString('base64'));

  const tri = pires.map(p => ({ p, l: lum(p[0], p[1], p[2]) })).sort((a, b) => a.l - b.l);
  const pire = tri[Math.floor(tri.length * 0.95)];
  const Lt = lum(255, 255, 255);
  const ratio = (Math.max(Lt, pire.l) + 0.05) / (Math.min(Lt, pire.l) + 0.05);
  // 3:1 est le seuil WCAG pour du grand texte ; on garde une marge.
  t(`contraste du sous-titre ≥ 3:1`, ratio >= 3,
    `${ratio.toFixed(2)}:1 sur fond rgb(${pire.p.join(',')})`);
  console.log(`         contraste mesuré : ${ratio.toFixed(2)}:1`);

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
