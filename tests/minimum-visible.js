// Le minimum de commande doit être annoncé dès la saisie de l'adresse, pas au
// dernier clic. C'est le constat le plus coûteux de l'audit : le client
// remplissait quatre écrans pour apprendre qu'il devait doubler sa commande.
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  const ouvrir = async () => {
    const ctx = await browser.newContext();
    await ctx.addInitScript(() => {
      const R = Date, f = new R('2026-09-11T14:00:00');
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
    await p.evaluate(() => openCommander());
    await p.waitForTimeout(300);
    await p.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await p.evaluate(() => { const r = document.getElementById('mode-livraison'); r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true })); });
    await p.waitForTimeout(150);
    return { ctx, p };
  };

  const saisir = async (p, adresse) => {
    await p.fill('#client-adresse', adresse);
    await p.evaluate(() => validateAdresse(document.getElementById('client-adresse')));
    await p.waitForTimeout(250);
    const z = p.locator('#min-commune');
    return (await z.isVisible()) ? (await z.innerText()).replace(/\s+/g, ' ').trim() : '';
  };

  // 1. Le minimum s'affiche dès l'adresse, avant toute pizza choisie.
  {
    const { ctx, p } = await ouvrir();
    t('rien affiché tant que l’adresse est vide', (await p.locator('#min-commune').isVisible()) === false);
    const mazan = await saisir(p, '5 avenue de la Republique, 84380 Mazan');
    t('Mazan : minimum annoncé dès la saisie', /4 grandes/.test(mazan) && /8 petites/.test(mazan), mazan);
    t('Mazan : la commune est nommée', /Mazan/.test(mazan), mazan);
    const carpentras = await saisir(p, '12 rue des Halles, 84200 Carpentras');
    t('Carpentras : le minimum suit l’adresse', /2 grandes/.test(carpentras), carpentras);
    const pernes = await saisir(p, '3 place Aristide Briand, 84210 Pernes-les-Fontaines');
    t('Pernes : 5 grandes, conforme au dépliant', /5 grandes/.test(pernes), pernes);
    const hors = await saisir(p, '25 rue Paradis, 13001 Marseille');
    t('hors zone : dit non et propose une issue',
      /ne livrons pas/i.test(hors) && /emporter/i.test(hors), hors);
    await ctx.close();
  }

  // 2. La barre de total dit en permanence ce qu'il manque.
  {
    const { ctx, p } = await ouvrir();
    await p.fill('#client-prenom', 'T'); await p.fill('#client-nom', 'A'); await p.fill('#client-tel', '0600000000');
    await saisir(p, '5 avenue de la Republique, 84380 Mazan');
    await p.evaluate(() => { const h = document.getElementById('client-heure'); if (h && h.options.length > 1) h.selectedIndex = 1; });
    await p.evaluate(() => nextStep(1));
    await p.waitForTimeout(400);
    const row = p.locator('#pizza-list .pizza-row').first();
    const lire = async () => (await p.locator('#sticky-count').innerText()).replace(/\s+/g, ' ').trim();

    await row.locator('.qty-btn.plus:visible').first().click();
    await row.locator('select.size-select').selectOption('30');
    await p.waitForTimeout(250);
    t('1 grande sur 4 : le manque est chiffré', /il manque 3 grandes/.test(await lire()), await lire());

    for (let i = 0; i < 3; i++) { await row.locator('.qty-btn.plus:visible').first().click(); await p.waitForTimeout(90); }
    t('4 grandes : minimum atteint', /minimum atteint/.test(await lire()), await lire());
    await ctx.close();
  }

  // 3. À emporter il n'y a pas de minimum : rien ne doit s'afficher.
  {
    const { ctx, p } = await ouvrir();
    await p.evaluate(() => { const r = document.getElementById('mode-emporter'); r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true })); });
    await p.waitForTimeout(200);
    t('à emporter : aucun minimum annoncé', (await p.locator('#min-commune').isVisible()) === false);
    await ctx.close();
  }

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
