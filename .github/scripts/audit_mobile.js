// Audit mobile du site, mesuré dans un vrai navigateur sur des écrans réels.
//
// Ce n'est pas une suite de tests : les suites de tests/ gardent des invariants
// connus et bloquent la publication. Celui-ci cherche ce que personne n'a
// encore regardé, sur toutes les pages, et se contente de rapporter.
//
//   node .github/scripts/audit_mobile.js [base]        (défaut : le site en ligne)
//
// Les faux positifs d'un audit coûtent plus cher que les trous : chaque mesure
// écarte explicitement ce qui n'est pas mesurable — texte posé sur une photo,
// diapositives d'un carrousel rangées hors écran, éléments animés, liens au fil
// d'une phrase que la norme WCAG exempte. Ce qui n'est pas mesurable est compté
// à part, jamais présenté comme un défaut.
const { chromium, devices } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.argv[2] || 'https://pizzanapolicarpentras.fr';
const UA = devices['iPhone 13'].userAgent;

// Deux états : le site change de visage à 17h30 (libellés, bouton d'appel).
const HEURES = { soir: '2026-11-18T21:40:00', jour: '2026-11-18T11:03:00' };

// 320 : iPhone SE première génération et Android d'entrée de gamme.
// 360 : la largeur la plus répandue du parc Android.
// 412 : grands Android. 740×360 : le même téléphone couché.
const ECRANS = [
  { nom: '320', l: 320, h: 568 },
  { nom: '360', l: 360, h: 740 },
  { nom: '375', l: 375, h: 667 },
  { nom: '412', l: 412, h: 915 },
  { nom: '740×360 (paysage)', l: 740, h: 360 },
];

// La liste des pages vient du sitemap du site visé : pas de fichier à tenir
// à jour, et l'audit suit l'arborescence réelle.
const listerPages = async (navigateur) => {
  const ctx = await navigateur.newContext();
  const p = await ctx.newPage();
  let liste = ['/'];
  try {
    const res = await p.goto(BASE + '/sitemap.xml', { waitUntil: 'load', timeout: 30000 });
    const xml = await res.text();
    // Le sitemap donne des adresses complètes vers le site en production.
    // On n'en garde que le chemin, sinon un audit joué sur une copie locale
    // irait interroger le site en ligne — ou nulle part.
    const trouve = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)]
      .map(m => { try { return new URL(m[1].trim()).pathname; } catch { return null; } })
      .filter(Boolean);
    if (trouve.length) liste = [...new Set(trouve)].sort();
  } catch (e) { /* pas de sitemap : on auditera l'accueil seul */ }
  await ctx.close();
  return liste;
};

const lum = (r, g, b) => {
  const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const ratio = (fg, bg) => {
  const m = fg.match(/[\d.]+/g), n = bg.match(/[\d.]+/g);
  if (!m || !n) return null;
  const a = m[3] !== undefined ? +m[3] : 1;
  const [br, bgr, bb] = [+n[0], +n[1], +n[2]];
  const fr = a * +m[0] + (1 - a) * br, fgg = a * +m[1] + (1 - a) * bgr, fb = a * +m[2] + (1 - a) * bb;
  const L1 = lum(fr, fgg, fb), L2 = lum(br, bgr, bb);
  return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
};

// ---------------------------------------------------------------- mesure DOM
// Tout ce qui suit s'exécute dans la page.
const RELEVE = function (largeur) {
  const vu = e => {
    const s = getComputedStyle(e);
    return s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity !== 0;
  };
  const feuilleTexte = e => e.children.length === 0 && e.textContent.trim().length > 0;
  // Un carrousel range ses diapositives côte à côte et n'en montre qu'une.
  const dansCarrousel = e => {
    for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) {
      const s = getComputedStyle(x);
      if (/hidden|auto|scroll|clip/.test(s.overflowX + s.overflow) &&
          x.clientWidth > 0 && x.scrollWidth >= x.clientWidth * 2) return true;
    }
    return false;
  };
  // Un tableau de prix qu'on fait défiler du doigt n'est pas du contenu perdu :
  // ce qui dépasse reste atteignable. On ne le compte donc pas comme rogné.
  const dansZoneDefilante = e => {
    for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) {
      const s = getComputedStyle(x);
      if (/auto|scroll/.test(s.overflowX) && x.clientWidth > 0 &&
          x.scrollWidth > x.clientWidth + 1) return true;
    }
    return false;
  };
  const anime = e => {
    for (let x = e; x && x !== document.body; x = x.parentElement) {
      if (getComputedStyle(x).transform !== 'none') return true;
    }
    return false;
  };
  // Fond réellement visible derrière un texte. null = non mesurable (photo,
  // dégradé, transparence partielle d'un ancêtre) : on ne prétend pas calculer
  // un contraste là-dessus.
  //
  // S'arrêter à la première couleur rencontrée était faux : un panneau en
  // rgba(255,255,255,.05) posé sur une section sombre se lisait comme un fond
  // blanc, et le texte blanc par-dessus ressortait à 1,00:1. Il faut empiler
  // les couches translucides jusqu'à la première opaque, puis les composer.
  const fond = e => {
    const couches = [];
    for (let x = e; x; x = x.parentElement) {
      const s = getComputedStyle(x);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null;
      // Une transparence partielle d'un ancêtre rend le fond incalculable.
      // Le seuil est bas exprès : les blocs qui apparaissent au défilement
      // passent par des valeurs intermédiaires, et la page est parcourue
      // avant la mesure pour qu'ils soient tous arrivés à 1.
      if (x !== e && +s.opacity < 0.9) return null;
      const m = (s.backgroundColor || '').match(/[\d.]+/g);
      if (!m) continue;
      const a = m[3] !== undefined ? +m[3] : 1;
      if (a === 0) continue;
      couches.push([+m[0], +m[1], +m[2], a]);
      if (a >= 0.999) break;
    }
    let r = 255, g = 255, b = 255;                    // la page est blanche en dessous
    for (let i = couches.length - 1; i >= 0; i--) {
      const [cr, cg, cb, ca] = couches[i];
      r = ca * cr + (1 - ca) * r; g = ca * cg + (1 - ca) * g; b = ca * cb + (1 - ca) * b;
    }
    return `rgb(${Math.round(r)}, ${Math.round(g)}, ${Math.round(b)})`;
  };
  // La couleur CSS ne décide pas du rendu d'un emoji : il est dessiné par la
  // police en couleurs. Mesurer son contraste n'a pas de sens.
  const queDesEmojis = t => !/[0-9A-Za-zÀ-ÿ]/.test(t);

  const r = {
    largeurMiseEnPage: window.innerWidth,
    largeurDocument: document.documentElement.scrollWidth,
    nbNoeuds: document.querySelectorAll('*').length,
    viewport: (document.querySelector('meta[name=viewport]') || {}).content || null,
    themeColor: !!document.querySelector('meta[name=theme-color]'),
    toucheIcone: !!document.querySelector('link[rel*="apple-touch-icon"]'),
    titre: document.title,
    horsEcran: [], petitTexte: [], contrasteFaible: [], contrasteNonMesurable: 0,
    ciblesPetites: [], champs: [], images: [], masqueFlottant: [],
    motsTropLongs: [],
  };

  // --- contenu rogné ---------------------------------------------------
  for (const e of document.querySelectorAll(
      'a, button, input, select, textarea, h1, h2, h3, h4, h5, h6, p, li, label, td, th, figcaption')) {
    const b = e.getBoundingClientRect();
    if (!b.width || !b.height || !vu(e)) continue;
    if (getComputedStyle(e).position === 'fixed') continue;
    if (e.classList.contains('skip-link') || dansCarrousel(e) || anime(e)) continue;
    if (dansZoneDefilante(e)) continue;
    if (!e.textContent.trim() && !/^(INPUT|SELECT|TEXTAREA)$/.test(e.tagName)) continue;
    const sortie = Math.round(Math.max(b.right - largeur, -b.left));
    if (sortie > 1) {
      r.horsEcran.push({ q: e.tagName.toLowerCase() + '.' + (e.className || '').toString().slice(0, 22),
                         px: sortie, t: e.textContent.trim().slice(0, 34) });
    }
  }

  // --- lisibilité ------------------------------------------------------
  for (const e of document.querySelectorAll('*')) {
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|TITLE)$/.test(e.tagName)) continue;
    if (!feuilleTexte(e) || !vu(e)) continue;
    if (e.classList.contains('skip-link')) continue;
    const s = getComputedStyle(e);
    const px = parseFloat(s.fontSize);
    const texte = e.textContent.trim();
    if (px && px < 12 && !queDesEmojis(texte)) {
      r.petitTexte.push({ px: +px.toFixed(1), q: e.tagName.toLowerCase() + '.' + (e.className || '').toString().slice(0, 20),
                          t: texte.slice(0, 30) });
    }
    const bg = queDesEmojis(texte) ? null : fond(e);
    if (bg === null) { r.contrasteNonMesurable++; }
    else {
      r.contrasteFaible.push({ fg: s.color, bg, px: +px.toFixed(1),
                               q: e.tagName.toLowerCase() + '.' + (e.className || '').toString().slice(0, 20),
                               t: texte.slice(0, 30),
                               gras: +s.fontWeight >= 700 });
    }
    // Un mot plus large que l'écran force un défilement latéral. On mesure la
    // largeur réelle : compter les caractères donnait des alertes sur des
    // adresses de site qui tenaient très bien dans l'écran.
    // 4 px de marge : un emoji dépasse souvent sa boîte de un ou deux
    // pixels, ce n'est pas un défaut de mise en page.
    if (e.scrollWidth > e.clientWidth + 4 && e.clientWidth > 0 && s.display !== 'inline' &&
        !/hidden|auto|scroll/.test(s.overflowX + s.overflow) && !dansCarrousel(e)) {
      const mots = texte.split(/\s+/).sort((a, b) => b.length - a.length);
      r.motsTropLongs.push({ t: (mots[0] || texte).slice(0, 40),
                             l: e.clientWidth, c: e.scrollWidth });
    }
  }

  // --- zones tactiles (WCAG 2.5.8) -------------------------------------
  // Une petite cible reste conforme si rien d'autre ne la serre : la règle
  // parle d'un disque de 24 px qui n'en recouvre pas un autre. Et les liens
  // au fil d'une phrase sont explicitement exemptés.
  const cibles = [];
  for (const e of document.querySelectorAll('a, button, input, select, textarea, [onclick]')) {
    const b = e.getBoundingClientRect();
    if (!b.width || !b.height || !vu(e) || e.classList.contains('skip-link')) continue;
    cibles.push({ e, b });
  }
  for (const { e, b } of cibles) {
    if (b.width >= 24 && b.height >= 24) continue;
    const p = e.parentElement;
    const dansPhrase = p && /^(P|LI|TD|SPAN|STRONG|EM|SMALL)$/.test(p.tagName) &&
      p.textContent.trim().length > e.textContent.trim().length + 12;
    if (dansPhrase) continue;
    const cx = b.left + b.width / 2, cy = b.top + b.height / 2;
    const serre = cibles.some(o => {
      if (o.e === e) return false;
      const ox = o.b.left + o.b.width / 2, oy = o.b.top + o.b.height / 2;
      return Math.hypot(cx - ox, cy - oy) < 24;
    });
    if (serre) {
      r.ciblesPetites.push({ q: e.tagName.toLowerCase() + '.' + (e.className || '').toString().slice(0, 20),
                             w: Math.round(b.width), h: Math.round(b.height),
                             t: e.textContent.trim().slice(0, 22) });
    }
  }

  // --- formulaires -----------------------------------------------------
  for (const e of document.querySelectorAll('input, select, textarea')) {
    if (e.type === 'hidden') continue;
    const s = getComputedStyle(e);
    r.champs.push({ id: e.id || e.name || '(sans nom)', type: e.type || e.tagName.toLowerCase(),
                    px: parseFloat(s.fontSize),
                    inputmode: e.getAttribute('inputmode'),
                    autocomplete: e.getAttribute('autocomplete'),
                    label: !!(e.id && document.querySelector(`label[for="${e.id}"]`)) ||
                           !!e.closest('label') || !!e.getAttribute('aria-label') });
  }

  // --- images ----------------------------------------------------------
  for (const img of document.querySelectorAll('img')) {
    const b = img.getBoundingClientRect();
    if (!b.width || !b.height) continue;
    r.images.push({ src: (img.currentSrc || img.src || '').split('/').pop().slice(0, 40),
                    nat: img.naturalWidth, aff: Math.round(b.width),
                    lazy: img.loading === 'lazy', srcset: !!img.srcset,
                    alt: img.alt !== null && img.alt !== '' });
  }

  // --- ce que les boutons flottants masquent en fin de page ------------
  const flot = document.querySelector('.float-group');
  if (flot) {
    document.querySelectorAll('#consent-banner, .cookie-banner').forEach(x => x.remove());
    document.documentElement.style.scrollBehavior = 'auto';
    document.body.style.scrollBehavior = 'auto';
    const boite = document.scrollingElement || document.documentElement;
    const bas = Math.max(document.body.scrollHeight, boite.scrollHeight);
    boite.scrollTop = bas; document.body.scrollTop = bas;
    window.scrollTo({ top: bas, behavior: 'instant' });
    const f = flot.getBoundingClientRect();
    r.flottant = { w: Math.round(f.width), h: Math.round(f.height),
                   defile: Math.round(Math.max(boite.scrollTop, document.body.scrollTop, window.scrollY)) };
    for (const e of document.querySelectorAll('a, p, li, h1, h2, h3, h4, span, div, td, th')) {
      if (!feuilleTexte(e) || !vu(e)) continue;
      if (getComputedStyle(e).position === 'fixed') continue;
      const b = e.getBoundingClientRect();
      if (!b.width || !b.height) continue;
      if (Math.min(b.right, f.right) - Math.max(b.left, f.left) > 2 &&
          Math.min(b.bottom, f.bottom) - Math.max(b.top, f.top) > 2) {
        r.masqueFlottant.push({ q: e.tagName.toLowerCase() + '.' + (e.className || '').toString().slice(0, 18),
                                t: e.textContent.trim().slice(0, 26) });
      }
    }
  }
  return r;
};

// ------------------------------------------------------------------ parcours
(async () => {
  const navigateur = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const pages = await listerPages(navigateur);
  const bilan = { pages: {}, poids: {}, erreurs: [], debut: Date.now() };

  const visiter = async (chemin, ecran, heure, mesurerPoids) => {
    const ctx = await navigateur.newContext({
      viewport: { width: ecran.l, height: ecran.h },
      isMobile: ecran.l < 700, hasTouch: true, deviceScaleFactor: 2, userAgent: UA,
    });
    await ctx.addInitScript(h => {
      const R = Date, f = new R(h);
      Date = class extends R { constructor(...a) { return a.length ? new R(...a) : new R(f); } static now() { return f.getTime(); } };
    }, heure);
    const p = await ctx.newPage();
    p.on('dialog', d => d.dismiss());
    const erreursJs = [];
    p.on('pageerror', e => erreursJs.push(String(e).slice(0, 120)));
    p.on('console', m => { if (m.type() === 'error') erreursJs.push('console: ' + m.text().slice(0, 120)); });
    const poids = { octets: 0, requetes: 0, parType: {} };
    if (mesurerPoids) {
      p.on('response', async res => {
        poids.requetes++;
        const t = (res.headers()['content-type'] || '?').split(';')[0];
        const n = +(res.headers()['content-length'] || 0);
        poids.octets += n;
        poids.parType[t] = (poids.parType[t] || 0) + n;
      });
    }
    const t0 = Date.now();
    let r = null;
    try {
      await p.goto(BASE + chemin, { waitUntil: 'load', timeout: 45000 });
      await p.waitForFunction(() => !document.getElementById('loader') ||
        document.getElementById('loader').classList.contains('hide'), { timeout: 12000 }).catch(() => {});
      const splash = Date.now() - t0;
      await p.waitForTimeout(700);
      // Parcourir la page avant de mesurer : les blocs qui apparaissent au
      // défilement restent sinon à mi-chemin de leur animation, et tout ce
      // qu'ils contiennent devient incalculable.
      await p.evaluate(async () => {
        document.documentElement.style.scrollBehavior = 'auto';
        document.body.style.scrollBehavior = 'auto';
        const boite = document.scrollingElement || document.documentElement;
        const haut = Math.max(document.body.scrollHeight, boite.scrollHeight);
        for (let y = 0; y < haut; y += Math.max(300, window.innerHeight * 0.8)) {
          boite.scrollTop = y; document.body.scrollTop = y;
          window.scrollTo({ top: y, behavior: 'instant' });
          await new Promise(r => setTimeout(r, 35));
        }
        boite.scrollTop = 0; document.body.scrollTop = 0;
        window.scrollTo({ top: 0, behavior: 'instant' });
      });
      await p.waitForTimeout(900);
      r = await p.evaluate(RELEVE, ecran.l);
      r.splash = splash;
      r.erreursJs = [...new Set(erreursJs)];
      if (mesurerPoids) r.poids = poids;
    } catch (e) {
      bilan.erreurs.push(`${chemin} ${ecran.nom} : ${String(e).slice(0, 120)}`);
    }
    await ctx.close();
    return r;
  };

  // Passe 1 : toutes les pages, 360 px, état du soir.
  console.log(`\n═══ passe 1 · ${pages.length} pages à 360 px ═══`);
  for (const chemin of pages) {
    const r = await visiter(chemin, ECRANS[1], HEURES.soir, false);
    if (r) bilan.pages[chemin] = { '360-soir': r };
    process.stdout.write('.');
  }
  console.log('');

  // Passe 2 : pages représentatives, toutes les largeurs, les deux états.
  const temoins = ['/', '/livraison-pizza-mazan/', '/pizzeria-carpentras/',
                   '/blog/guide-mazan.html', '/cgv/'].filter(c => pages.includes(c) || pages.length === 1);
  console.log(`═══ passe 2 · ${temoins.length} pages × ${ECRANS.length} largeurs × 2 états ═══`);
  for (const chemin of temoins) {
    for (const ecran of ECRANS) {
      for (const [nomH, h] of Object.entries(HEURES)) {
        if (ecran !== ECRANS[1] && nomH === 'jour' && chemin !== '/') continue;
        const r = await visiter(chemin, ecran, h, ecran === ECRANS[1] && nomH === 'soir');
        if (r) {
          bilan.pages[chemin] = bilan.pages[chemin] || {};
          bilan.pages[chemin][`${ecran.nom}-${nomH}`] = r;
        }
        process.stdout.write('.');
      }
    }
  }
  console.log('');

  bilan.duree = Math.round((Date.now() - bilan.debut) / 1000);
  bilan.ratio = ratio.toString();
  fs.writeFileSync(process.env.SORTIE || 'audit-mobile.json', JSON.stringify(bilan, null, 1));
  console.log(`\nRelevé écrit dans ${process.env.SORTIE || 'audit-mobile.json'} · ${bilan.duree} s`);
  await navigateur.close();
})();
