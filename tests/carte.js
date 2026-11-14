// La carte affichée par le formulaire doit être celle du dépliant imprimé.
// On lit le menu rendu dans le navigateur, pas le code source : c'est ce que
// le client voit qui compte.
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';
const fs = require('fs');
const path = require('path');

const CARTE = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '.github', 'data', 'carte.json'), 'utf8'));
const cle = n => n.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
  .replace(/[^a-z0-9]+/g, ' ').trim();

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext();
  await ctx.addInitScript(() => {
    const R = Date, f = new R('2026-09-11T14:00:00');
    Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
  });
  const page = await ctx.newPage();
  page.on('dialog', d => d.dismiss());
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });

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

  // Les offres elles-mêmes sont couvertes par tests/offres-boisson.js : ici on
  // ne vérifie que ce que le bandeau annonce au visiteur.
  const banniere = await page.locator('.promo-banner').innerText();   // le CSS le met en capitales
  t('bandeau conforme au dépliant',
    /0,50/.test(banniere) && /5 pizzas/i.test(banniere), banniere);

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
