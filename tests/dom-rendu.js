const { chromium } = require('playwright');
const PAGES = ['/','/pizzeria-carpentras/','/livraison-pizza-mazan/','/blog/pizza-artisanale-carpentras/','/blog/guide-mazan.html'];
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
  let ko = 0;
  for (const p of PAGES) {
    const ctx = await b.newContext(); const page = await ctx.newPage();
    await page.goto('http://127.0.0.1:8899' + p, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);
    const r = await page.evaluate(() => {
      const m = document.querySelector('main#main-content');
      const h1 = document.querySelector('h1');
      const ban = document.getElementById('consent-banner');
      const pb = ban && ban.querySelector('p');
      const lum = c => { const [r,g,bl] = c.match(/\d+/g).map(Number).map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);}); return 0.2126*r+0.7152*g+0.0722*bl; };
      let ratio = null;
      if (pb) { const s = getComputedStyle(pb), sb = getComputedStyle(ban);
        const l1 = lum(s.color), l2 = lum(sb.backgroundColor);
        ratio = +(((Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05)).toFixed(2)); }
      return { main: !!m, mainVide: m ? m.innerText.trim().length === 0 : null,
               h1DansMain: !!(m && h1 && m.contains(h1)), contraste: ratio };
    });
    const bon = r.main && !r.mainVide && r.h1DansMain && (r.contraste === null || r.contraste >= 4.5);
    if (!bon) ko++;
    console.log(`  ${bon ? 'OK   ' : 'ECHEC'} ${p.padEnd(38)} main:${r.main} vide:${r.mainVide} h1-dedans:${r.h1DansMain} contraste:${r.contraste}`);
    await ctx.close();
  }
  console.log(`\n  ${PAGES.length - ko}/${PAGES.length} conformes`);
  await b.close();
})();
