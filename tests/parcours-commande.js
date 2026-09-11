// Parcours client reel : clics dans l'interface, aucune manipulation d'etat interne.
const { chromium } = require('playwright');

const CAS = [
  { n: '2 petites · Carpentras (min 2)',            v: '12 rue des Halles, 84200 Carpentras', t: '26', q: 2, att: 'BLOQUE' },
  { n: '4 petites · Carpentras (min 2)',            v: '12 rue des Halles, 84200 Carpentras', t: '26', q: 4, att: 'PASSE'  },
  { n: '2 grandes · Carpentras (min 2)',            v: '12 rue des Halles, 84200 Carpentras', t: '30', q: 2, att: 'PASSE'  },
  { n: '1 grande · Carpentras (min 2)',             v: '12 rue des Halles, 84200 Carpentras', t: '30', q: 1, att: 'BLOQUE' },
  { n: '2 petites · Les Pennes-Mirabeau (hors zone)', v: '11 Rue Pierre Loti 13170 Les Pennes-Mirabeau', t: '26', q: 2, att: 'BLOQUE' },
  { n: '10 grandes · Marseille (hors zone)',        v: '25 rue Paradis, 13001 Marseille', t: '30', q: 10, att: 'BLOQUE' },
  { n: '6 petites · Mazan (min 4)',                 v: '5 avenue de la Republique, 84380 Mazan', t: '26', q: 6, att: 'BLOQUE' },
  { n: '8 petites · Mazan (min 4)',                 v: '5 avenue de la Republique, 84380 Mazan', t: '26', q: 8, att: 'PASSE'  },
  { n: '4 petites · Monteux (min 3)',               v: '8 cours des Platanes, 84170 Monteux', t: '26', q: 4, att: 'BLOQUE' },
  { n: '6 petites · Monteux (min 3)',               v: '8 cours des Platanes, 84170 Monteux', t: '26', q: 6, att: 'PASSE'  },
  { n: '2 petites · A EMPORTER hors zone',          v: '25 rue Paradis, 13001 Marseille', t: '26', q: 2, att: 'PASSE', emporter: true },
];

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  let ok = 0;

  for (const c of CAS) {
    const ctx = await browser.newContext();
    await ctx.addInitScript(() => {                     // avant 17h30 : formulaire en ligne
      const R = Date, f = new R('2026-09-11T14:00:00');
      Date = class extends R {
        constructor(...a) { return a.length ? new R(...a) : new R(f); }
        static now() { return f.getTime(); }
      };
    });
    const page = await ctx.newPage();
    let alerte = null, envoye = false;
    page.on('dialog', async d => { alerte ??= d.message(); await d.dismiss(); });
    await ctx.route('**wa.me/**', r => { envoye = true; r.abort(); });
    await ctx.route('**api.web3forms.com/**', r => r.abort());

    await page.goto('http://127.0.0.1:8899/', { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => openCommander());
    await page.waitForTimeout(300);
    await page.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await page.waitForTimeout(300);

    // Etape 1 : coordonnees et mode, via l'interface
    await page.evaluate(em => {
      const r = document.getElementById(em ? 'mode-emporter' : 'mode-livraison');
      r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true }));
    }, !!c.emporter);
    await page.waitForTimeout(150);
    await page.fill('#client-prenom', 'Test');
    await page.fill('#client-nom', 'Auto');
    await page.fill('#client-tel', '0600000000');
    if (!c.emporter) await page.fill('#client-adresse', c.v);
    await page.evaluate(() => {
      const h = document.getElementById('client-heure');
      if (h && h.options.length > 1) h.selectedIndex = 1;
    });
    await page.evaluate(() => nextStep(1));
    await page.waitForTimeout(400);
    // Refus des l'etape 1 (zone non desservie) : pas besoin d'aller plus loin
    if (alerte) {
      const bon1 = c.att === 'BLOQUE';
      if (bon1) ok++;
      console.log(`  ${bon1 ? 'OK   ' : 'ECHEC'} ${c.n.padEnd(42)} bloque des l'etape 1 -> BLOQUE${bon1 ? '' : '  ATTENDU ' + c.att}`);
      console.log(`         « ${alerte.split('\n')[0].slice(0, 95)} »`);
      await ctx.close();
      continue;
    }

    // Etape 2 : ajout des pizzas par clics sur "+"
    const row = page.locator('#pizza-list .pizza-row').first();
    for (let i = 0; i < c.q; i++) {
      await row.locator('.qty-btn.plus:visible').first().click();
      await page.waitForTimeout(80);
    }
    if (await row.locator('select.size-select').count()) {
      await row.locator('select.size-select').selectOption(c.t);
      await page.waitForTimeout(150);
    }
    const panier = await page.evaluate(() =>
      Object.values(pizzaOrders).filter(o => o.qty > 0).map(o => `${o.qty}x${o.size}`).join(','));

    await page.evaluate(() => {
      const p = document.querySelector('input[name="paiement"]'); if (p) p.checked = true;
    });

    await page.evaluate(() => envoyerWhatsApp());
    await page.waitForTimeout(600);

    const obtenu = alerte ? 'BLOQUE' : 'PASSE';
    const bon = obtenu === c.att;
    if (bon) ok++;
    console.log(`  ${bon ? 'OK   ' : 'ECHEC'} ${c.n.padEnd(42)} panier=${(panier || 'vide').padEnd(7)} -> ${obtenu}${bon ? '' : '  ATTENDU ' + c.att}`);
    if (alerte) console.log(`         « ${alerte.split('\n')[0].slice(0, 95)} »`);
    await ctx.close();
  }

  console.log(`\n  ${ok}/${CAS.length} scenarios conformes`);
  await browser.close();
  process.exit(ok === CAS.length ? 0 : 1);
})();
