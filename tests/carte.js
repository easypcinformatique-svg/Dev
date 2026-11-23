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

  // La carte affichée sur la page d'accueil est une SECONDE liste, écrite à la
  // main à côté du formulaire. Les deux avaient divergé sans que rien ne le
  // voie : la Bergère annonçait « mozzarella » dans sa fiche et
  // « champignons » dans le formulaire, sur la même page, et c'est une cliente
  // qui l'a signalé. On compare désormais les deux listes entre elles.
  const fiches = await page.evaluate(() => [...document.querySelectorAll('.menu-card')].map(k => {
    const prix = [...k.querySelectorAll('.price-item')].map(i => ({
      taille: (i.querySelector('.price-size') || {}).textContent || '',
      val: (i.querySelector('.price-val') || {}).textContent || '' }));
    return { nom: (k.querySelector('h3') || {}).textContent.trim(),
             ingr: (k.querySelector('p') || {}).textContent.trim(), prix };
  }));
  t('la page affiche bien une carte', fiches.length > 50, `${fiches.length} fiches`);

  const montant = s => {
    const m = String(s).replace('€', ',').match(/[\d]+(?:,\d+)?/);
    return m ? parseFloat(m[0].replace(',', '.')) : null;
  };
  const ecartsFiches = [];
  for (const f of fiches) {
    const ref = CARTE.pizzas[Object.keys(CARTE.pizzas).find(n => cle(n) === cle(f.nom))];
    if (!ref) continue;                       // desserts et recettes hors dépliant
    if (f.ingr !== ref.ingredients.trim())
      ecartsFiches.push(`${f.nom} : fiche « ${f.ingr} » ≠ dépliant « ${ref.ingredients} »`);
    for (const p of f.prix) {
      const attendu = /petite/i.test(p.taille) ? ref.petite : ref.grande;
      if (attendu == null) continue;
      if (Math.abs((montant(p.val) ?? -1) - attendu) > 0.005)
        ecartsFiches.push(`${f.nom} : ${p.taille.trim()} affichée ${p.val}, dépliant ${attendu}`);
    }
  }
  t('les fiches de la page d’accueil disent la même chose que le dépliant',
    ecartsFiches.length === 0, `${ecartsFiches.length} écart(s)`);
  ecartsFiches.slice(0, 8).forEach(e => console.log(`         ${e}`));

  // Et le point de départ : fiche et formulaire d'accord entre eux.
  const desaccords = [];
  for (const f of fiches) {
    const vu = menu.find(p => cle(p.name) === cle(f.nom));
    if (!vu) continue;
    if (f.ingr !== vu.ingr.trim())
      desaccords.push(`${f.nom} : fiche « ${f.ingr} » ≠ formulaire « ${vu.ingr} »`);
    for (const p of f.prix) {
      const attendu = /petite/i.test(p.taille) ? vu.p26 : vu.p30;
      if (attendu == null) continue;
      if (Math.abs((montant(p.val) ?? -1) - attendu) > 0.005)
        desaccords.push(`${f.nom} : ${p.taille.trim()} ${p.val} ≠ formulaire ${attendu}`);
    }
  }
  t('la fiche et le formulaire ne se contredisent pas', desaccords.length === 0,
    `${desaccords.length} contradiction(s)`);
  desaccords.slice(0, 8).forEach(e => console.log(`         ${e}`));
  t('Bergère : champignons, pas mozzarella',
    (fiches.find(f => cle(f.nom) === cle('Bergère')) || {}).ingr === 'Fromage, crème, chèvre, champignons',
    (fiches.find(f => cle(f.nom) === cle('Bergère')) || {}).ingr);

  // Les offres elles-mêmes sont couvertes par tests/offres-boisson.js : ici on
  // ne vérifie que ce que le bandeau annonce au visiteur.
  const banniere = await page.locator('.promo-banner').innerText();   // le CSS le met en capitales
  t('bandeau conforme au dépliant',
    /0,50/.test(banniere) && /5 pizzas/i.test(banniere), banniere);

  // La bande de chiffres de l'accueil : le nombre vit dans un attribut et le
  // libellé dans un élément voisin, donc rien ne les tenait d'accord. Le
  // compteur d'avis était resté à 526 quand le site en affichait 582 partout.
  const chiffres = await page.evaluate(() =>
    [...document.querySelectorAll('.counter-box')].map(b => ({
      n: (b.querySelector('.counter-num') || {}).textContent?.trim(),
      cible: (b.querySelector('.counter-num') || {}).getAttribute?.('data-target'),
      lbl: (b.querySelector('.counter-lbl') || {}).textContent?.trim() || '',
    })));
  const source = await page.evaluate(() => {
    const m = document.documentElement.innerHTML.match(/"reviewCount":"(\d+)"/);
    return { avis: m ? m[1] : null, recettes: PIZZAS.length };
  });
  const trouve = l => chiffres.find(c => new RegExp(l, 'i').test(c.lbl));
  const avis = trouve('avis');
  t('compteur d’avis accordé au balisage',
    avis && avis.n === source.avis && avis.cible === source.avis,
    avis ? `affiché ${avis.n} / cible ${avis.cible} / source ${source.avis}` : 'compteur absent');
  const recettes = trouve('recette|pizza');
  t('compteur de recettes accordé à la carte',
    recettes && +recettes.n === source.recettes,
    recettes ? `${recettes.n} pour ${source.recettes} entrées` : 'compteur absent');
  t('aucun compteur ne dit « pizzas » pour le menu entier',
    !chiffres.some(c => /pizzas/i.test(c.lbl) && +c.n === source.recettes),
    chiffres.map(c => `${c.n} ${c.lbl}`).join(' · '));
  const ans = trouve("ans d");
  t('années d’expérience justes',
    ans && +ans.n === new Date().getFullYear() - 2008,
    ans ? `${ans.n} ans` : 'compteur absent');

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
