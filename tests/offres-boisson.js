// Les offres du dépliant doivent être proposées pendant la commande, au bon
// palier, et se retrouver dans le total comme dans le message envoyé.
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';
const fs = require('fs');
const path = require('path');

const CARTE = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '.github', 'data', 'carte.json'), 'utf8'));

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  // Mène une commande jusqu'à l'étape boissons avec n pizzas, puis décrit l'offre.
  const jusquAuxBoissons = async (n) => {
    const ctx = await browser.newContext();
    await ctx.addInitScript(() => {
      const R = Date, f = new R('2026-09-11T14:00:00');
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await ctx.route('**wa.me/**', r => r.abort());
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await p.evaluate(() => openCommander());
    await p.waitForTimeout(300);
    await p.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await p.evaluate(() => { const r = document.getElementById('mode-livraison'); r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true })); });
    await p.fill('#client-prenom', 'T'); await p.fill('#client-nom', 'A'); await p.fill('#client-tel', '0600000000');
    await p.fill('#client-adresse', '12 rue des Halles, 84200 Carpentras');
    await p.evaluate(() => { const h = document.getElementById('client-heure'); if (h && h.options.length > 1) h.selectedIndex = 1; });
    await p.evaluate(() => nextStep(1));
    await p.waitForTimeout(400);
    const row = p.locator('#pizza-list .pizza-row').first();
    for (let i = 0; i < n; i++) { await row.locator('.qty-btn.plus:visible').first().click(); await p.waitForTimeout(60); }
    await row.locator('select.size-select').selectOption('30');
    await p.evaluate(() => nextStep(2));
    await p.waitForTimeout(500);
    return { ctx, p };
  };

  const decrire = async (n) => {
    const { ctx, p } = await jusquAuxBoissons(n);
    const visible = await p.locator('#offres-boisson').isVisible();
    const titre = visible ? await p.locator('#offre-detail').innerText() : '';
    const choix = visible ? await p.locator('#offre-choix button').allInnerTexts() : [];
    const evin = visible ? await p.locator('#offre-evin').isVisible() : false;
    await ctx.close();
    return { visible, titre, choix, evin };
  };

  const deux = await decrire(2);
  t('aucune offre à 2 pizzas', deux.visible === false);

  const trois = await decrire(3);
  t('palier 3 pizzas proposé', trois.visible && /0,50/.test(trois.titre), trois.titre);
  t('palier 3 : pas de rosé', !trois.choix.some(c => /rosé/i.test(c)), trois.choix.join(', '));
  t('palier 3 : pas de mention alcool', trois.evin === false);

  const cinq = await decrire(5);
  t('palier 5 pizzas proposé', cinq.visible && /offert/.test(cinq.titre), cinq.titre);
  t('palier 5 : rosé proposé', cinq.choix.some(c => /rosé/i.test(c)), cinq.choix.join(', '));
  t('palier 5 : mention loi Évin affichée', cinq.evin === true);

  // L'offre doit se retrouver dans le total et dans le message envoyé.
  {
    const { ctx, p } = await jusquAuxBoissons(5);
    let corps = null;
    await ctx.route('**api.web3forms.com/**', r => { corps = r.request().postData(); r.abort(); });
    const avant = await p.locator('#sticky-amount').innerText();
    await p.locator('#offre-choix button').first().click();
    await p.waitForTimeout(300);
    const apres = await p.locator('#sticky-amount').innerText();
    t('fenêtre fermée après le choix', !(await p.locator('#offres-boisson').isVisible()));
    t('offerte : le total ne bouge pas', avant === apres, `${avant} -> ${apres}`);
    await p.evaluate(() => { const r = document.querySelector('input[name="paiement"]'); if (r) r.checked = true; });
    await p.evaluate(() => envoyerWhatsApp());
    await p.waitForTimeout(700);
    const msg = corps ? JSON.parse(corps).message : '';
    t('offre reportée dans la commande', /OFFRE :/.test(msg) && /offert/.test(msg),
      (msg.match(/OFFRE :.*/) || [''])[0]);
    await ctx.close();
  }

  // Le palier payant doit bien ajouter 0,50 € — c'est de l'argent.
  {
    const { ctx, p } = await jusquAuxBoissons(3);
    const avant = await p.locator('#sticky-amount').innerText();
    await p.locator('#offre-choix button').first().click();
    await p.waitForTimeout(300);
    const apres = await p.locator('#sticky-amount').innerText();
    const cts = s => parseFloat(s.replace(',', '.').replace('€', '').trim());
    t('palier 3 : +0,50 € au total', Math.abs(cts(apres) - cts(avant) - 0.5) < 0.001,
      `${avant} -> ${apres}`);
    await ctx.close();
  }

  // Le refus doit être respecté.
  {
    const { ctx, p } = await jusquAuxBoissons(5);
    await p.locator('#offres-boisson button:has-text("Non merci")').click();
    await p.waitForTimeout(200);
    await p.evaluate(() => nextStep(2));
    await p.waitForTimeout(400);
    t('« Non merci » respecté', !(await p.locator('#offres-boisson').isVisible()));
    await ctx.close();
  }

  // La carte des boissons doit être celle du dépliant.
  {
    const ctx = await browser.newContext();
    const p = await ctx.newPage();
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    const vues = await p.evaluate(() => DRINKS.map(d => `${d.name}|${d.price}`));
    const attendues = CARTE.boissons.map(b => `${b.nom}|${b.prix}`);
    t(`${attendues.length} boissons conformes au dépliant`,
      JSON.stringify(vues) === JSON.stringify(attendues),
      vues.filter((v, i) => v !== attendues[i]).join(' ; '));
    await ctx.close();
  }

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
