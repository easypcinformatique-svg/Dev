// Vérifie le comportement réel du consentement : cookies avant / après choix.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const analytics = c => c.filter(k => /^_ga|^_gid|^_gat/.test(k.name));
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  // 1. Visiteur qui n'a pas encore choisi
  let ctx = await browser.newContext();
  let page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  const visible = await page.locator('#consent-banner').isVisible();
  let cookies = analytics(await ctx.cookies());
  t('bandeau affiché au premier passage', visible);
  t('aucun cookie de mesure avant choix', cookies.length === 0, cookies.map(c => c.name).join(','));

  // 2. Refus
  await page.click('#consent-no');
  await page.waitForTimeout(1200);
  cookies = analytics(await ctx.cookies());
  t('bandeau masqué après refus', !(await page.locator('#consent-banner').isVisible()));
  t('aucun cookie après refus', cookies.length === 0, cookies.map(c => c.name).join(','));
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  t('refus mémorisé au rechargement', !(await page.locator('#consent-banner').isVisible()));
  t('toujours aucun cookie', analytics(await ctx.cookies()).length === 0);
  await ctx.close();

  // 3. Acceptation
  ctx = await browser.newContext();
  page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(800);
  await page.click('#consent-yes');
  await page.waitForTimeout(1500);
  // googletagmanager est injoignable depuis le bac à sable, donc le cookie _ga
  // ne peut pas être observé ici : on vérifie le contrat du site, la séquence
  // poussée dans dataLayer, que gtag consommera une fois le script chargé.
  const dl = await page.evaluate(() =>
    (window.dataLayer || []).map(a => Array.from(a)).filter(a => a[0] === 'consent'));
  t('consentement refusé par défaut',
    dl.some(a => a[1] === 'default' && a[2].analytics_storage === 'denied'));
  t('consentement accordé après acceptation',
    dl.some(a => a[1] === 'update' && a[2].analytics_storage === 'granted'));
  t('choix mémorisé', !(await page.locator('#consent-banner').isVisible()));
  await ctx.close();

  // 4. Le bandeau ne casse pas la commande
  ctx = await browser.newContext();
  await ctx.addInitScript(() => {
    const R = Date, f = new R('2026-09-11T14:00:00');
    Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
  });
  page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => openCommander());
  await page.waitForTimeout(400);
  t('formulaire de commande toujours ouvrable', await page.locator('#order-overlay.open').count() > 0);
  await ctx.close();

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
