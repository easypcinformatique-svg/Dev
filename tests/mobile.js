// Compatibilité smartphone, mesurée dans un vrai navigateur mobile : débordement
// horizontal, taille des zones tactiles, lisibilité du texte, et le tunnel de
// commande utilisable au pouce. L'audit de septembre excluait ce périmètre.
const { chromium, devices } = require('playwright');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8899';

const PAGES = [
  ['/', 'accueil'],
  ['/livraison-pizza-mazan/', 'page commune'],
  ['/blog/guide-mazan.html', 'guide'],
  ['/pizzeria-carpentras/', 'pizzeria'],
  ['/cgv/', 'CGV'],
];
// 360 px d'abord : c'est la largeur des Galaxy A et de la plupart des Android
// d'entrée de gamme, plus étroite que l'iPhone SE. Elle manquait, et c'est
// elle qui a montré le bouton d'appel coupé des deux côtés.
const ECRANS = [
  { nom: 'petit 320', largeur: 320, hauteur: 568 },
  { nom: 'Android 360', largeur: 360, hauteur: 800 },
  { nom: 'iPhone SE', largeur: 375, hauteur: 667 },
  { nom: 'iPhone 14', largeur: 390, hauteur: 844 },
  { nom: 'Android large', largeur: 412, hauteur: 915 },
];

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  let ok = 0, total = 0, details = [];
  const t = (nom, cond, detail = '') => {
    total++; if (cond) ok++;
    console.log(`  ${cond ? 'OK   ' : 'ECHEC'} ${nom}${cond || !detail ? '' : '   (' + detail + ')'}`);
  };

  const mesurer = async (chemin, ecran) => {
    const ctx = await browser.newContext({
      viewport: { width: ecran.largeur, height: ecran.hauteur },
      isMobile: true, hasTouch: true, deviceScaleFactor: 2,
      userAgent: devices['iPhone 13'].userAgent,
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + chemin, { waitUntil: 'load' });
    await p.waitForFunction(() => !document.getElementById('loader') ||
      document.getElementById('loader').classList.contains('hide'), { timeout: 9000 }).catch(() => {});
    await p.waitForTimeout(900);
    const r = await p.evaluate(() => {
      const de = document.documentElement;
      const trop = [];
      // Quels éléments dépassent réellement la largeur de l'écran ?
      for (const e of document.querySelectorAll('body *')) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        if (b.right > window.innerWidth + 1 || b.left < -1) {
          const s = getComputedStyle(e);
          if (s.position === 'fixed' || s.visibility === 'hidden' || s.display === 'none') continue;
          trop.push({ tag: e.tagName.toLowerCase(), cls: (e.className || '').toString().slice(0, 34),
                      debord: Math.round(Math.max(b.right - window.innerWidth, -b.left)) });
        }
      }
      // Contenu rogné. Le test ne regardait que la largeur du document : un
      // élément qui sort de l'écran mais que son parent masque ne l'élargit
      // pas, donc le bouton d'appel a pu rester coupé des deux côtés sans
      // qu'une seule vérification bronche. On regarde ici ce que le visiteur
      // perd vraiment — du texte et des commandes, pas une image décorative
      // volontairement agrandie (celles-là portent une transformation).
      // Un carrousel range ses diapositives côte à côte et n'en montre qu'une :
      // ses voisines sont hors écran exprès. Signature : un parent qui masque
      // son débordement et dont le contenu fait au moins le double de sa
      // largeur. Le hero, lui, masque aussi son débordement mais ne dépasse
      // que de quelques dizaines de pixels — le bouton rogné reste donc vu.
      const dansCarrousel = e => {
        for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) {
          const s = getComputedStyle(x);
          if (/hidden|auto|scroll/.test(s.overflowX + s.overflow) &&
              x.scrollWidth >= x.clientWidth * 2 && x.clientWidth > 0) return true;
        }
        return false;
      };
      const rogne = [];
      for (const e of document.querySelectorAll(
          'a, button, input, select, textarea, h1, h2, h3, h4, h5, h6, p, li, label, td, th')) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        const s = getComputedStyle(e);
        if (s.position === 'fixed' || s.visibility === 'hidden' || s.display === 'none') continue;
        if (s.transform !== 'none') continue;
        if (e.classList.contains('skip-link')) continue;   // hors champ exprès
        if (dansCarrousel(e)) continue;
        if (!e.textContent.trim() && !/^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) continue;
        const sortie = Math.round(Math.max(b.right - window.innerWidth, -b.left));
        if (sortie > 1) {
          rogne.push(`${e.tagName.toLowerCase()}.${(e.className || '').toString().slice(0, 24)}` +
                     ` +${sortie}px « ${e.textContent.trim().slice(0, 26)} »`);
        }
      }
      // Zones tactiles trop petites. La norme WCAG 2.5.8 exempte les liens au
      // fil d'une phrase et les cibles masquées : les compter donnerait un
      // chiffre spectaculaire et faux.
      const petites = [];
      for (const e of document.querySelectorAll('a, button, input, select, textarea, [onclick]')) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        if (getComputedStyle(e).display === 'none') continue;
        if (e.classList.contains('skip-link')) continue;          // mesuré à part, ci-dessous
        const p = e.parentElement;
        const dansPhrase = p && /^(P|LI|TD|SPAN|STRONG|EM|SMALL)$/.test(p.tagName)
          && p.textContent.trim().length > e.textContent.trim().length + 12;
        if (dansPhrase) continue;
        if (b.height < 24 || b.width < 24) {
          petites.push(`${e.tagName.toLowerCase()}.${(e.className || '').toString().slice(0, 20)} ${Math.round(b.width)}×${Math.round(b.height)}`);
        }
      }
      // Texte trop petit pour être lu sans zoomer
      const minus = [];
      for (const e of document.querySelectorAll('p, li, span, td, label, a')) {
        if (!e.textContent.trim() || e.children.length) continue;
        const px = parseFloat(getComputedStyle(e).fontSize);
        if (px && px < 12) minus.push(`${px.toFixed(1)}px « ${e.textContent.trim().slice(0, 28)} »`);
      }
      // Le lien d'évitement n'avait aucune règle CSS : il s'affichait en texte
      // nu tout en haut de chaque page. Il doit être hors champ au repos et
      // revenir au premier plan quand le clavier l'atteint.
      const saut = document.querySelector('.skip-link');
      let evitement = null;
      if (saut) {
        const r = saut.getBoundingClientRect();
        saut.focus();
        const f = saut.getBoundingClientRect();
        saut.blur();
        evitement = { cacheAuRepos: r.right <= 0 || r.bottom <= 0 || r.left >= window.innerWidth,
                      visibleAuClavier: f.right > 0 && f.left < window.innerWidth && f.height > 0 };
      }
      // L'en-tête recouvre la bannière : le nom de la pizzeria doit rester
      // dessous. La marge était un nombre fixe calé sur l'en-tête d'un jour ;
      // une ligne de plus dans le bandeau d'offre l'aurait masqué.
      const entete = document.querySelector('nav');
      const titre = document.querySelector('.hero-panneau');
      let recouvrement = null;
      if (entete && titre) {
        recouvrement = Math.round(entete.getBoundingClientRect().bottom -
                                  titre.getBoundingClientRect().top);
      }
      return {
        evitement, recouvrement,
        rogne: [...new Set(rogne)].slice(0, 6), nbRogne: rogne.length,
        largeurDoc: de.scrollWidth, largeurEcran: window.innerWidth,
        debordements: trop.slice(0, 6), nbDebord: trop.length,
        petites: [...new Set(petites)].slice(0, 6), nbPetites: petites.length,
        minus: [...new Set(minus)].slice(0, 4), nbMinus: minus.length,
        viewport: !!document.querySelector('meta[name="viewport"]'),
      };
    });
    await ctx.close();
    return r;
  };

  for (const ecran of ECRANS) {
    console.log(`\n── ${ecran.nom} (${ecran.largeur} px) ──`);
    for (const [chemin, nom] of PAGES) {
      const r = await mesurer(chemin, ecran);
      // Comparer à window.innerWidth était un angle mort : quand le contenu
      // réclame plus que l'écran, le navigateur mobile ÉLARGIT la fenêtre de
      // mise en page et rétrécit la page pour la faire entrer. innerWidth vaut
      // alors la largeur élargie, le test trouvait l'égalité et ne voyait rien
      // — pendant que le téléphone affichait tout en plus petit, bandeau
      // d'offre rogné compris. On compare donc à la largeur réelle de l'écran.
      const deborde = r.largeurDoc > ecran.largeur + 1 || r.largeurEcran > ecran.largeur + 1;
      t(`${nom.padEnd(13)} tient dans la largeur de l’écran`, !deborde,
        deborde ? `mise en page sur ${r.largeurEcran} px, document ${r.largeurDoc} px, ` +
                  `écran ${ecran.largeur} px` : '');
      // Bloquant, sur les quatre largeurs : du texte ou un bouton rogné est
      // invisible pour le visiteur, que la page défile ou non.
      t(`${nom.padEnd(13)} aucun texte ni bouton rogné`, r.nbRogne === 0,
        r.nbRogne ? `${r.nbRogne} — ${r.rogne.join(' · ')}` : '');
      if (r.recouvrement !== null) {
        t(`${nom.padEnd(13)} l’en-tête ne recouvre pas la bannière`, r.recouvrement <= 0,
          `l’en-tête descend ${r.recouvrement} px trop bas`);
      }
      if (deborde || r.nbDebord) {
        details.push(`${ecran.nom} ${chemin} : ${r.nbDebord} élément(s) hors écran — ` +
          r.debordements.map(d => `${d.tag}.${d.cls} +${d.debord}px`).join(', '));
      }
      if (r.nbPetites) details.push(`${ecran.nom} ${chemin} : ${r.nbPetites} zone(s) tactile(s) < 24px — ${r.petites.join(' · ')}`);
      if (r.nbMinus) details.push(`${ecran.nom} ${chemin} : ${r.nbMinus} texte(s) < 12px — ${r.minus.join(' · ')}`);
      if (ecran === ECRANS[0]) {
        t(`${nom.padEnd(13)} balise viewport présente`, r.viewport);
        // Ces deux plafonds étaient l'état constaté, pas un idéal : 21 libellés
        // sous 12 px sur l'accueil, 18 cibles trop petites sur le guide. Tout a
        // été repris le 16/11/2026, le plafond est donc zéro — un seul libellé
        // qui repasserait sous la barre arrêterait la publication.
        const plafondTactile = 0;
        const plafondTexte = 0;
        t(`${nom.padEnd(13)} zones tactiles : pas de régression`, r.nbPetites <= plafondTactile,
          `${r.nbPetites} sous 24 px, plafond ${plafondTactile}`);
        t(`${nom.padEnd(13)} petits textes : pas de régression`, r.nbMinus <= plafondTexte,
          `${r.nbMinus} sous 12 px, plafond ${plafondTexte}`);
        t(`${nom.padEnd(13)} lien d’évitement caché, puis visible au clavier`,
          !r.evitement || (r.evitement.cacheAuRepos && r.evitement.visibleAuClavier),
          r.evitement ? `repos=${r.evitement.cacheAuRepos} clavier=${r.evitement.visibleAuClavier}` : '');
      }
    }
  }

  // Le tunnel de commande au pouce
  console.log('\n── tunnel de commande sur iPhone SE ──');
  {
    const ctx = await browser.newContext({
      viewport: { width: 375, height: 667 }, isMobile: true, hasTouch: true,
      deviceScaleFactor: 2, userAgent: devices['iPhone 13'].userAgent });
    await ctx.addInitScript(() => {
      const R = Date, f = new R('2026-11-16T14:00:00');
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    });
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    await p.goto(BASE + '/', { waitUntil: 'load' });
    await p.waitForFunction(() => document.getElementById('loader')?.classList.contains('hide'), { timeout: 9000 });
    await p.waitForTimeout(700);
    await p.evaluate(() => openCommander());
    await p.waitForTimeout(400);
    await p.evaluate(() => document.querySelector('#pre-order-notice.show') && dismissNotice());
    await p.waitForTimeout(300);
    t('le formulaire s’ouvre', await p.locator('#order-overlay.open').count() > 0);
    const champ = await p.locator('#client-prenom').boundingBox();
    t('les champs tiennent dans l’écran', champ && champ.x >= 0 && champ.x + champ.width <= 376,
      champ ? `x=${Math.round(champ.x)} largeur=${Math.round(champ.width)}` : 'champ absent');
    const taille = await p.evaluate(() => parseFloat(getComputedStyle(document.getElementById('client-tel')).fontSize));
    // En dessous de 16 px, iOS zoome automatiquement à la saisie.
    t('saisie sans zoom automatique iOS (≥16 px)', taille >= 16, `${taille}px`);
    const dep = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    t('formulaire sans débordement', dep <= 1, `${dep}px`);
    await ctx.close();
  }

  if (details.length) {
    console.log('\n── détail des écarts ──');
    [...new Set(details)].slice(0, 14).forEach(d => console.log('   ' + d));
  }
  console.log(`\n  ${ok}/${total} conformes`);
  await browser.close();
  process.exit(ok === total ? 0 : 1);
})();
