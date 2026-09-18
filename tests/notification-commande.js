// Vérifie ce que le site envoie réellement à Web3Forms : c'est cet e-mail qui
// atterrissait dans les spams. On passe une vraie commande dans l'interface et
// on inspecte le corps de la requête, pas le code source.
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  const ctx = await browser.newContext();
  await ctx.addInitScript(() => {                       // avant 17h30 : formulaire en ligne
    const R = Date, f = new R('2026-09-11T14:00:00');
    Date = class extends R {
      constructor(...a) { return a.length ? new R(...a) : new R(f); }
      static now() { return f.getTime(); }
    };
  });
  const page = await ctx.newPage();
  let corps = null;
  page.on('dialog', d => d.dismiss());
  await ctx.route('**wa.me/**', r => r.abort());
  await ctx.route('**api.web3forms.com/**', r => { corps = r.request().postData(); r.abort(); });

  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => openCommander());
  await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());

  // 2 grandes à Carpentras : minimum atteint, la commande part.
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const r = document.getElementById('mode-livraison');
    r.checked = true; r.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForTimeout(150);
  await page.fill('#client-prenom', 'Alice');
  await page.fill('#client-nom', 'Morello');
  await page.fill('#client-tel', '0699272160');
  await page.fill('#client-adresse', '12 rue des Halles, 84200 Carpentras');
  await page.evaluate(() => {
    const h = document.getElementById('client-heure');
    if (h && h.options.length > 1) h.selectedIndex = 1;
  });
  await page.evaluate(() => nextStep(1));
  await page.waitForTimeout(400);

  const row = page.locator('#pizza-list .pizza-row').first();
  for (let i = 0; i < 2; i++) { await row.locator('.qty-btn.plus:visible').first().click(); await page.waitForTimeout(80); }
  if (await row.locator('select.size-select').count()) {
    await row.locator('select.size-select').selectOption('30');
    await page.waitForTimeout(150);
  }
  await page.evaluate(() => {
    const p = document.querySelector('input[name="paiement"]'); if (p) p.checked = true;
  });
  await page.evaluate(() => envoyerWhatsApp());
  await page.waitForTimeout(800);

  let ok = 0, total = 0;
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  t('la commande déclenche bien la notification', corps !== null);
  const p = corps ? JSON.parse(corps) : {};
  t('objet préfixé COMMANDE SITE', /^COMMANDE SITE - /.test(p.subject || ''), p.subject);
  // Un objet sans emoji évite un signal de spam classique ; le symbole € reste.
  t('objet sans emoji', !/\p{Extended_Pictographic}/u.test(p.subject || ''), p.subject);
  t('nom d\'expéditeur défini', p.from_name === 'Commandes Pizza Napoli', p.from_name);
  t('réponse dirigée vers la pizzeria', p.replyto === 'carpentraspizzanapoli@gmail.com', p.replyto);
  t('clé d\'accès toujours transmise', !!p.access_key);
  t('contenu de la commande intact', /NOUVELLE COMMANDE/.test(p.message || ''));
  t('client et total dans l\'objet', /Alice Morello/.test(p.subject || '') && /€/.test(p.subject || ''), p.subject);

  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
