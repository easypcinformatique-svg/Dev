// La carte affichée par le formulaire doit être celle du dépliant imprimé.
// On lit le menu rendu dans le navigateur, pas le code source : c'est ce que
// le client voit qui compte.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const CARTE = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '.github', 'data', 'carte.json'), 'utf8'));
const cle = n => n.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9]+/g, ' ').trim();

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const ctx = await browser.newContext();
  await ctx.addInitScript(() => {
    const R = Date, f = new R('2026-09-11T14:00:00');
    Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
  });
  const page = await ctx.newPage();
  page.on('dialog', d => d.dismiss());
  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'domcontentloaded' });

  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  // Le tableau PIZZAS est ce que le formulaire consomme pour construire la carte.
  const menu = await page.evaluate(() => PIZZAS.map(p => ({
    name: p.name, ingr: p.ingr, p26: p.p26, p30: p.p30 })));
  const parCle = new Map(menu.map(p => [p.name, p]));

  const ecarts = [];
  for (const [nom, ref] of Object.entries(CARTE.pizzas)) {
    const vu = menu.find(p => cle(p.name) === cle(nom));
    if (!vu) { ecarts.push(`${nom} : absente du formulaire`); continue; }
    if (vu.ingr.trim() !== ref.ingredients.trim())
      ecarts.push(`${nom} : « ${vu.ingr} » au lieu de « ${ref.ingredients} »`);
    if ((vu.p26 ?? null) !== (ref.petite ?? null))
      ecarts.push(`${nom} : petite ${vu.p26} au lieu de ${ref.petite}`);
    if ((vu.p30 ?? null) !== (ref.grande ?? null))
      ecarts.push(`${nom} : grande ${vu.p30} au lieu de ${ref.grande}`);
  }
  t(`${Object.keys(CARTE.pizzas).length} recettes du dépliant conformes`, ecarts.length === 0);
  ecarts.slice(0, 8).forEach(e => console.log(`         ${e}`));

  const connus = new Set([...Object.keys(CARTE.pizzas), ...CARTE.hors_depliant_conservees].map(cle));
  const intrus = menu.filter(p => !connus.has(cle(p.name))).map(p => p.name);
  t('aucune recette inconnue du dépliant', intrus.length === 0, intrus.join(', '));
  t('aucun doublon de nom', parCle.size === menu.length);
  t('« Raviole Basilic » renommée', !menu.some(p => p.name === 'Raviole Basilic'));
  t('Margherita petite à 7,00 €', (menu.find(p => p.name === 'Margherita') || {}).p26 === 7);

  // L'offre boisson : le compteur lisait une classe absente de la page, donc
  // la fenêtre ne s'ouvrait jamais. Elle doit s'ouvrir à 5 pizzas, pas avant.
  const essai = async (n) => {
    const c2 = await browser.newContext();
    await c2.addInitScript(() => {
      const R = Date, f = new R('2026-09-11T14:00:00');
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    });
    const p2 = await c2.newPage();
    p2.on('dialog', d => d.dismiss());
    await p2.goto('http://127.0.0.1:8899/', { waitUntil: 'domcontentloaded' });
    await p2.evaluate(() => openCommander());
    await p2.waitForTimeout(300);
    await p2.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await p2.evaluate(() => { const r = document.getElementById('mode-livraison'); r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true })); });
    await p2.fill('#client-prenom', 'T'); await p2.fill('#client-nom', 'A'); await p2.fill('#client-tel', '0600000000');
    await p2.fill('#client-adresse', '12 rue des Halles, 84200 Carpentras');
    await p2.evaluate(() => { const h = document.getElementById('client-heure'); if (h && h.options.length > 1) h.selectedIndex = 1; });
    await p2.evaluate(() => nextStep(1));
    await p2.waitForTimeout(400);
    const row = p2.locator('#pizza-list .pizza-row').first();
    for (let i = 0; i < n; i++) { await row.locator('.qty-btn.plus:visible').first().click(); await p2.waitForTimeout(60); }
    await p2.evaluate(() => nextStep(2));
    await p2.waitForTimeout(500);
    const vu = await p2.locator('#free-bottle-popup').isVisible();
    await c2.close();
    return vu;
  };
  t('pas de boisson offerte à 4 pizzas', (await essai(4)) === false);
  t('boisson offerte proposée à 5 pizzas', (await essai(5)) === true);

  const banniere = await page.locator('.promo-banner').innerText();   // le CSS le met en capitales
  t('bandeau conforme au dépliant',
    /0,50/.test(banniere) && /5 pizzas/i.test(banniere), banniere);

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
