// Le bouton principal doit dire ce qu'il fait : le formulaire avant 17h30,
// le téléphone après — puisque le tunnel est fermé pendant le service.
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  const a = async (heure) => {
    const ctx = await browser.newContext();
    await ctx.addInitScript(h => {
      const R = Date, f = new R(h);
      Date = class extends R { constructor(...x) { return x.length ? new R(...x) : new R(f); } static now() { return f.getTime(); } };
    }, heure);
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + '/', { waitUntil: 'load' });
    await p.waitForTimeout(500);
    const cta = p.locator('a.nav-cta').first();
    const r = {
      libelle: (await cta.innerText()).trim(),
      href: await cta.getAttribute('href'),
      // Un lien en pleine phrase ne doit pas être réécrit.
      phrase: await p.locator('a[onclick*="openCommander"]:has-text("formulaire en ligne")').count()
        ? (await p.locator('a[onclick*="openCommander"]:has-text("formulaire en ligne")').first().innerText()).trim()
        : '(absent)',
    };
    await ctx.close();
    return r;
  };

  const jour = await a('2026-09-11T14:00:00');
  t('avant 17h30 : le bouton propose de commander', /Commander/i.test(jour.libelle), jour.libelle);
  t('avant 17h30 : pas de lien tel:', jour.href !== 'tel:0761083608', jour.href);

  const soir = await a('2026-09-11T19:00:00');
  t('après 17h30 : le bouton annonce l\'appel', /Appeler/i.test(soir.libelle), soir.libelle);
  t('après 17h30 : le numéro est dans le libellé', /07 61 08 36 08/.test(soir.libelle), soir.libelle);
  t('après 17h30 : un seul geste, le lien appelle', soir.href === 'tel:0761083608', soir.href);
  t('les liens en pleine phrase sont intacts', soir.phrase === jour.phrase, `${jour.phrase} / ${soir.phrase}`);

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
