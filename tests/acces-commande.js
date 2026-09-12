const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  let ok = 0, total = 0;
  const t = (n, c, d='') => { total++; if (c) ok++; console.log(`  ${c?'OK   ':'ECHEC'} ${n}${c||!d?'':'   ('+d+')'}`); };

  for (const dep of ['/livraison-pizza-mazan/', '/blog/guide-mazan.html']) {
    const ctx = await b.newContext();
    await ctx.addInitScript(() => { const R=Date,f=new R('2026-09-12T14:00:00');
      Date = class extends R { constructor(...a){return a.length?new R(...a):new R(f);} static now(){return f.getTime();} }; });
    const page = await ctx.newPage();
    await page.goto('http://127.0.0.1:8899' + dep, { waitUntil: 'domcontentloaded' });
    const lien = page.locator('.commander-inline a');
    t(`CTA present sur ${dep}`, await lien.count() > 0);
    const href = await lien.first().getAttribute('href');
    // suit le lien en local
    await page.goto('http://127.0.0.1:8899/#commander', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    const ouvert = await page.locator('#order-overlay.open').count();
    t(`formulaire ouvert via #commander (depuis ${dep.slice(0,22)})`, ouvert > 0, 'overlay ferme');
    await ctx.close();
  }
  // apres 17h30 : modale telephone, pas le formulaire
  const ctx2 = await b.newContext();
  await ctx2.addInitScript(() => { const R=Date,f=new R('2026-09-12T19:00:00');
    Date = class extends R { constructor(...a){return a.length?new R(...a):new R(f);} static now(){return f.getTime();} }; });
  const p2 = await ctx2.newPage();
  await p2.goto('http://127.0.0.1:8899/#commander', { waitUntil: 'domcontentloaded' });
  await p2.waitForTimeout(1200);
  t('apres 17h30 : modale telephone', await p2.locator('#phone-order-modal.open').count() > 0);
  await ctx2.close();
  console.log(`\n  ${ok}/${total} conformes`);
  await b.close();
})();
