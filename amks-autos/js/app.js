/* AMKS Autos : comportement du site (aucune dépendance, aucune donnée envoyée à un serveur). */
(function () {
  "use strict";
  var C = window.AMKS;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  var MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."];
  var euro = function (n) { return n.toLocaleString("fr-FR") + " €"; };
  var pad = function (n) { return (n < 10 ? "0" : "") + n; };
  var iso = function (d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); };
  var frDate = function (d) { return d.getDate() + " " + MOIS[d.getMonth()] + " " + d.getFullYear(); };
  var toMin = function (hhmm) { var p = hhmm.split(":"); return +p[0] * 60 + +p[1]; };
  var hm = function (m) { return pad(Math.floor(m / 60)) + "h" + pad(m % 60); };

  function toast(msg) {
    var t = $("#toast"); t.textContent = msg; t.classList.add("on");
    clearTimeout(toast.t); toast.t = setTimeout(function () { t.classList.remove("on"); }, 2600);
  }

  /* ---------- Coordonnées injectées depuis config.js ---------- */
  var adresse = C.adresse.rue + ", " + C.adresse.cp + " " + C.adresse.ville;
  $$("[data-k='depuis']").forEach(function (e) { e.textContent = C.depuis; });
  $$("[data-k='cp']").forEach(function (e) { e.textContent = C.adresse.cp; });
  $$("[data-k='quartier']").forEach(function (e) { e.textContent = C.adresse.quartier; });
  $$("[data-k='adresse-ligne']").forEach(function (e) { e.textContent = adresse + " · " + C.telephone; });
  $$("[data-k='forme-ligne']").forEach(function (e) { e.textContent = C.raisonSociale + ", " + C.forme + " au capital de " + C.capital + " · " + C.rcs; });
  $$(".tel-link").forEach(function (a) { a.href = "tel:+" + C.telephoneIntl; a.textContent = C.telephone; });
  $$(".mail-link").forEach(function (a) { a.href = "mailto:" + C.email; a.textContent = C.email; });
  var callTop = $("#call-top"); if (callTop) { callTop.href = "tel:+" + C.telephoneIntl; $(".call-num", callTop).textContent = C.telephone; }
  var itin = $("#itin"); if (itin) itin.href = "https://www.google.com/maps/dir/?api=1&destination=" + encodeURIComponent(adresse);
  var waD = $("#wa-direct"); if (waD) waD.href = "https://wa.me/" + C.telephoneIntl + "?text=" + encodeURIComponent("Bonjour AMKS Autos, ");

  /* ---------- Horaires et statut en direct ---------- */
  function plages(d) { return C.fermetures.indexOf(iso(d)) >= 0 ? [] : (C.horaires[d.getDay()] || []); }
  function statut() {
    var now = new Date(), m = now.getHours() * 60 + now.getMinutes(), p = plages(now), el = $("#status");
    if (!el) return;
    for (var i = 0; i < p.length; i++) {
      var a = toMin(p[i][0]), b = toMin(p[i][1]);
      if (m >= a && m < b) {
        el.className = "status open";
        $("span", el).textContent = b - m <= 30 ? "Ouvert, ferme à " + hm(b) : "Ouvert jusqu'à " + hm(b);
        return;
      }
    }
    for (var k = 0; k < 8; k++) {
      var d = new Date(now); d.setDate(d.getDate() + k);
      var pp = plages(d);
      for (var j = 0; j < pp.length; j++) {
        if (k > 0 || toMin(pp[j][0]) > m) {
          el.className = "status closed";
          $("span", el).textContent = "Fermé · ouvre " + (k === 0 ? "à " : k === 1 ? "demain à " : JOURS[d.getDay()] + " à ") + hm(toMin(pp[j][0]));
          return;
        }
      }
    }
  }
  statut(); setInterval(statut, 60000);

  var tbl = $("#hours");
  if (tbl) {
    var today = new Date().getDay();
    [1, 2, 3, 4, 5, 6, 0].forEach(function (j) {
      var p = C.horaires[j] || [], tr = document.createElement("tr");
      if (j === today) tr.className = "today";
      tr.innerHTML = "<td>" + JOURS[j].charAt(0).toUpperCase() + JOURS[j].slice(1) + "</td><td>" +
        (p.length ? p.map(function (x) { return x[0].replace(":", "h") + " – " + x[1].replace(":", "h"); }).join(" · ") : "Fermé") + "</td>";
      tbl.appendChild(tr);
    });
  }

  /* ---------- Menu mobile ---------- */
  var burger = $("#burger"), nav = $("#nav");
  burger.addEventListener("click", function () {
    var o = nav.classList.toggle("open"); burger.setAttribute("aria-expanded", o);
  });
  $$("a", nav).forEach(function (a) { a.addEventListener("click", function () { nav.classList.remove("open"); burger.setAttribute("aria-expanded", "false"); }); });

  /* ---------- Services ---------- */
  var ICO = {
    carrosserie: '<path d="M3 15h18M5 15l1.5-5A2 2 0 0 1 8.4 8.5h7.2a2 2 0 0 1 1.9 1.5L19 15M5 15v3h2v-2M19 15v3h-2v-2"/><circle cx="7.5" cy="13" r=".6"/><circle cx="16.5" cy="13" r=".6"/>',
    peinture: '<path d="M4 20l6-6M9 9l6 6M14 4l6 6-5 5-6-6zM10 14l-2.5 2.5"/>',
    mecanique: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    entretien: '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    sinistre: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    vo: '<path d="M4 7h16v10H4zM8 7V5h8v2M8 12h8"/>'
  };
  var SERVICES = [
    { id: "carrosserie", t: "Carrosserie", p: "Chocs, rayures, bosses : redressage ou remplacement des éléments.", l: ["Débosselage et redressage", "Pare-chocs, ailes, portières", "Remplacement de vitrage", "Réparation plastique"] },
    { id: "peinture", t: "Peinture en cabine", p: "Cabine pressurisée à brûleur : finition sans poussière, séchage maîtrisé.", l: ["Raccord teinte au code constructeur", "Peinture d'élément ou complète", "Vernis et lustrage", "Rénovation d'optiques"] },
    { id: "mecanique", t: "Mécanique", p: "Diagnostic électronique et réparation, toutes marques.", l: ["Freinage : plaquettes, disques", "Trains roulants, rotules, triangles", "Admission, FAP, vanne EGR", "Embrayage et distribution"] },
    { id: "entretien", t: "Entretien", p: "Révision selon le plan constructeur, carnet tamponné.", l: ["Vidange et filtres", "Contrôle des niveaux", "Géométrie", "Préparation au contrôle technique"] },
    { id: "sinistre", t: "Sinistres et assurances", p: "Accueil de l'expert, chiffrage, réparation après accord.", l: ["Libre choix du réparateur", "Suivi du dossier avec l'expert", "Vous ne payez que la franchise", "Gardiennage du véhicule"] },
    { id: "vo", t: "Achat et vente", p: "Véhicules d'occasion révisés et recherche sur mesure.", l: ["Véhicules révisés avant vente", "Reprise de votre véhicule", "Recherche selon votre budget", "Démarches de carte grise"] }
  ];
  var g = $("#svc-grid");
  SERVICES.forEach(function (s) {
    var el = document.createElement("article"); el.className = "svc";
    el.innerHTML = '<div class="svc-ico"><svg viewBox="0 0 24 24" aria-hidden="true">' + ICO[s.id] + '</svg></div><h3>' + s.t + "</h3><p>" + s.p + "</p><ul>" +
      s.l.map(function (x) { return "<li>" + x + "</li>"; }).join("") + '</ul><button class="link" type="button" data-svc="' + s.t + '">Demander un devis</button>';
    g.appendChild(el);
  });
  g.addEventListener("click", function (e) {
    var b = e.target.closest("[data-svc]"); if (!b) return;
    openWizard(b.dataset.svc === "Sinistres et assurances" ? "sinistre" : b.dataset.svc === "Achat et vente" ? "vehicule" : "devis", b.dataset.svc);
  });

  /* ---------- Forfaits ---------- */
  var fl = $("#forfaits-list");
  C.forfaits.forEach(function (f) {
    var el = document.createElement("div"); el.className = "forfait";
    el.innerHTML = "<b>" + f.nom + "</b><small>" + f.detail + '</small><span class="prix">' +
      (f.prix == null ? "Sur devis" : "<small>dès</small>" + euro(f.prix)) + "</span>";
    fl.appendChild(el);
  });

  /* ---------- Plaque d'immatriculation ---------- */
  function formatPlaque(v) {
    var s = v.toUpperCase().replace(/[^A-Z0-9]/g, "");
    if (/^[A-Z]{1,2}/.test(s)) { // SIV AA-123-AA
      var a = s.slice(0, 2), b = s.slice(2, 5), c = s.slice(5, 7);
      return a + (b ? "-" + b : "") + (c ? "-" + c : "");
    }
    return v.toUpperCase().slice(0, 9); // ancien format FNI : laissé tel quel
  }
  var plaqueOK = function (v) { return /^[A-HJ-NP-TV-Z]{2}-\d{3}-[A-HJ-NP-TV-Z]{2}$/.test(v) && !/^(SS|WW)/.test(v) || /^\d{1,4}\s?[A-Z]{1,3}\s?\d{2,3}$/.test(v); };
  function bindPlaque(inp, hint) {
    inp.addEventListener("input", function () {
      var p = inp.selectionStart === inp.value.length; inp.value = formatPlaque(inp.value);
      if (p) inp.setSelectionRange(inp.value.length, inp.value.length);
      if (!hint) return;
      if (!inp.value) { hint.className = "plate-hint"; hint.textContent = "Format SIV : deux lettres, trois chiffres, deux lettres."; }
      else if (plaqueOK(inp.value)) { hint.className = "plate-hint ok"; hint.textContent = "Immatriculation valide."; }
      else { hint.className = "plate-hint"; hint.textContent = "Continuez la saisie…"; }
    });
  }
  bindPlaque($("#plate-in"), $("#plate-hint")); bindPlaque($("#wz-plaque"));
  $("#plate-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var v = $("#plate-in").value;
    if (v && !plaqueOK(v)) { var h = $("#plate-hint"); h.className = "plate-hint err"; h.textContent = "Cette immatriculation semble incomplète. Exemple : AB-123-CD."; return; }
    $("#wz-plaque").value = v; openWizard("devis");
  });
  $("#plate-ct").addEventListener("click", function () { location.hash = ""; $("#echeances").scrollIntoView(); setTimeout(function () { $("#ech-mec").focus(); }, 400); });

  /* ---------- Échéances du véhicule ---------- */
  var addMonths = function (d, n) { var r = new Date(d); var day = r.getDate(); r.setDate(1); r.setMonth(r.getMonth() + n); r.setDate(Math.min(day, new Date(r.getFullYear(), r.getMonth() + 1, 0).getDate())); return r; };
  var parse = function (v) { if (!v) return null; var p = v.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); };
  function icsEvent(title, d, desc) {
    var dt = iso(d).replace(/-/g, ""), uid = dt + "-" + title.replace(/\W/g, "") + "@amks-autos";
    var stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, "");
    return ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp, "DTSTART;VALUE=DATE:" + dt, "SUMMARY:" + title, "DESCRIPTION:" + desc.replace(/\n/g, "\\n"),
      "LOCATION:AMKS Autos\\, " + adresse.replace(/,/g, "\\,"), "BEGIN:VALARM", "TRIGGER:-P7D", "ACTION:DISPLAY", "DESCRIPTION:" + title, "END:VALARM", "END:VEVENT"].join("\r\n");
  }
  function icsFile(events) { return ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AMKS Autos//Echeances//FR", "CALSCALE:GREGORIAN"].concat(events).concat(["END:VCALENDAR"]).join("\r\n"); }
  function download(name, text, link) {
    var url = URL.createObjectURL(new Blob([text], { type: "text/calendar;charset=utf-8" }));
    link.href = url; link.download = name;
  }

  function renderEcheances(e) {
    if (e) e.preventDefault();
    var out = $("#ech-out"), mec = parse($("#ech-mec").value), ct = parse($("#ech-ct").value), rev = parse($("#ech-rev").value), km = +$("#ech-km").value || 12000;
    var now = new Date(); now.setHours(0, 0, 0, 0);
    if (!mec) {
      out.innerHTML = '<div class="ech-empty"><h3>Exemple</h3><p>Une voiture immatriculée le 15 mars 2022 passe son premier contrôle technique avant le 15 mars 2026, puis tous les deux ans. Renseignez la date de votre carte grise pour obtenir vos dates.</p></div>';
      return;
    }
    if (mec > now) { out.innerHTML = '<div class="ech-empty">La date de première immatriculation est dans le futur : vérifiez la case B de la carte grise.</div>'; return; }
    var items = [];
    var ctDue, ctNote;
    if (ct) { ctDue = addMonths(ct, 24); ctNote = "Deux ans après le dernier contrôle du " + frDate(ct) + "."; }
    else {
      ctDue = addMonths(mec, 48); ctNote = "Premier contrôle : dans les 6 mois avant les 4 ans du véhicule.";
      if (ctDue < now) { while (ctDue < now) ctDue = addMonths(ctDue, 24); ctNote = "Calcul fait sans date de dernier contrôle : renseignez-la pour une date exacte."; }
    }
    items.push({ t: "Contrôle technique", d: ctDue, n: ctNote + " Contre-visite éventuelle sous 2 mois." });
    if (rev) {
      var mois = Math.min(12, Math.max(3, Math.round(15000 / km * 12)));
      items.push({ t: "Révision", d: addMonths(rev, mois), n: "Tous les " + mois + " mois ou 15 000 km avec " + km.toLocaleString("fr-FR") + " km par an. Vérifiez le plan de votre constructeur." });
    }
    items.sort(function (a, b) { return a.d - b.d; });
    out.innerHTML = "";
    items.forEach(function (it) {
      var j = Math.round((it.d - now) / 864e5), cls = j < 0 ? "bad" : j <= 60 ? "warn" : "";
      var label = j < 0 ? "En retard de " + (-j) + " j" : j === 0 ? "Aujourd'hui" : j <= 60 ? "Dans " + j + " jours" : "Dans " + Math.round(j / 30.4) + " mois";
      var el = document.createElement("article"); el.className = "ech-card " + cls;
      el.innerHTML = '<div class="ech-date"><b>' + pad(it.d.getDate()) + "</b><span>" + MOIS[it.d.getMonth()] + " " + it.d.getFullYear() + "</span></div><h3>" + it.t + '</h3><span class="pill">' + label + "</span><p>" + it.n + "</p>";
      out.appendChild(el);
    });
    var act = document.createElement("div"); act.className = "ech-actions";
    act.innerHTML = '<a class="btn btn-outline" id="ech-ics">Ajouter à mon agenda</a><a class="btn btn-signal" href="#demande">Réserver à l\'atelier</a>';
    out.appendChild(act);
    download("echeances-vehicule.ics", icsFile(items.map(function (it) { return icsEvent(it.t + " : véhicule", it.d, it.n + "\nAMKS Autos : " + C.telephone); })), $("#ech-ics"));
    $("#ech-ics").addEventListener("click", function () { toast("Fichier agenda téléchargé : ouvrez-le pour ajouter les rappels."); });
    try { localStorage.setItem("amks-ech", JSON.stringify({ mec: $("#ech-mec").value, ct: $("#ech-ct").value, rev: $("#ech-rev").value, km: km })); } catch (x) {}
  }
  try { var sv = JSON.parse(localStorage.getItem("amks-ech") || "null"); if (sv) { $("#ech-mec").value = sv.mec || ""; $("#ech-ct").value = sv.ct || ""; $("#ech-rev").value = sv.rev || ""; $("#ech-km").value = sv.km || 12000; } } catch (x) {}
  $("#ech-form").addEventListener("submit", renderEcheances);
  renderEcheances();

  /* ---------- Véhicules d'occasion ---------- */
  var stock = [];
  function renderStock() {
    var grid = $("#occ-grid"), en = $("#occ-energie").value, max = +$("#occ-max").value || Infinity, tri = $("#occ-tri").value;
    grid.innerHTML = "";
    if (!stock.length) {
      grid.innerHTML = '<div class="occ-empty"><div><h3>Recherche sur mesure</h3><p>Aucun véhicule en vitrine pour le moment. Donnez-nous la marque, le budget et le kilométrage souhaités : nous cherchons, contrôlons et révisons le véhicule avant de vous le présenter.</p></div><a class="btn btn-signal" href="#demande" data-type="vehicule">Lancer ma recherche</a></div>';
      return;
    }
    var list = stock.filter(function (v) { return (!en || v.energie === en) && v.prix <= max; })
      .sort(function (a, b) { return tri === "annee" ? b.annee - a.annee : a[tri] - b[tri]; });
    if (!list.length) { grid.innerHTML = '<p class="ech-empty" style="grid-column:1/-1">Aucun véhicule ne correspond à ces filtres.</p>'; return; }
    list.forEach(function (v) {
      var el = document.createElement("article"); el.className = "car";
      el.innerHTML = '<div class="car-ph">' + (v.photo ? '<img src="' + v.photo + '" alt="' + v.marque + " " + v.modele + '" loading="lazy">' : "Photo à venir") + '</div><div class="car-body"><h3>' + v.marque + " " + v.modele +
        '</h3><div class="car-spec"><span>' + v.annee + "</span><span>" + v.km.toLocaleString("fr-FR") + " km</span><span>" + v.energie + "</span><span>" + v.boite + "</span></div><p>" + (v.description || "") +
        '</p><div class="car-prix">' + euro(v.prix) + '</div><button class="btn btn-outline" type="button">Ce véhicule m\'intéresse</button></div>';
      $("button", el).addEventListener("click", function () { $("#wz-desc").value = "Intéressé par : " + v.marque + " " + v.modele + " " + v.annee + ", " + euro(v.prix) + "."; openWizard("vehicule"); });
      grid.appendChild(el);
    });
  }
  ["#occ-energie", "#occ-tri", "#occ-max"].forEach(function (s) { $(s).addEventListener("input", renderStock); });
  renderStock();
  fetch("data/vehicules.json", { cache: "no-store" }).then(function (r) { return r.ok ? r.json() : null; })
    .then(function (j) { if (j && j.vehicules && j.vehicules.length) { stock = j.vehicules; $("#occ-tools").hidden = false; renderStock(); } }).catch(function () {});

  /* ---------- Assistant de demande ---------- */
  var TRAVAUX = {
    devis: ["Carrosserie", "Peinture en cabine", "Mécanique", "Freinage", "Embrayage", "Pare-brise", "Climatisation"],
    rdv: ["Révision", "Vidange", "Diagnostic électronique", "Géométrie", "Freinage", "Pré-contrôle technique", "Pneumatiques"],
    sinistre: ["Choc avant", "Choc arrière", "Choc latéral", "Rayures / vandalisme", "Grêle", "Bris de glace"],
    vehicule: ["Achat d'occasion", "Reprise de mon véhicule", "Recherche sur mesure"]
  };
  var page = 0, choix = { jour: null, heure: null }, wiz = $("#wizard");
  var typeVal = function () { return ($("input[name=type]:checked", wiz) || {}).value || "devis"; };

  function renderChips(preselect) {
    var box = $("#wz-travaux"); box.innerHTML = "";
    TRAVAUX[typeVal()].forEach(function (t) {
      var b = document.createElement("button"); b.type = "button"; b.className = "chip"; b.textContent = t;
      b.setAttribute("aria-pressed", preselect && (t === preselect || preselect.indexOf(t) === 0) ? "true" : "false");
      b.addEventListener("click", function () { b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true"); });
      box.appendChild(b);
    });
    $("#wz-assur-box").hidden = typeVal() !== "sinistre";
  }
  $$("input[name=type]", wiz).forEach(function (r) { r.addEventListener("change", function () { renderChips(); }); });

  function renderDays() {
    var box = $("#wz-days"); box.innerHTML = "";
    var d = new Date(); d.setHours(0, 0, 0, 0); var n = 0, guard = 0;
    while (n < 10 && guard++ < 30) {
      var p = plages(d);
      if (p.length && slotsFor(d).some(function (s) { return !s.off; })) {
        var b = document.createElement("button"); b.type = "button"; b.className = "day"; b.setAttribute("role", "option");
        b.dataset.iso = iso(d); b.setAttribute("aria-selected", choix.jour === b.dataset.iso);
        b.innerHTML = "<small>" + JOURS[d.getDay()].slice(0, 3) + "</small><b>" + d.getDate() + "</b><small>" + MOIS[d.getMonth()] + "</small>";
        box.appendChild(b); n++;
      }
      d.setDate(d.getDate() + 1);
    }
    if (!choix.jour && box.firstChild) { choix.jour = box.firstChild.dataset.iso; box.firstChild.setAttribute("aria-selected", "true"); }
    renderSlots();
  }
  function slotsFor(d) {
    var out = [], now = new Date(), isToday = iso(d) === iso(now), nowM = now.getHours() * 60 + now.getMinutes() + 60;
    plages(d).forEach(function (p) {
      for (var m = toMin(p[0]); m + C.creneauMinutes <= toMin(p[1]); m += C.creneauMinutes) out.push({ m: m, off: isToday && m < nowM });
    });
    return out;
  }
  function renderSlots() {
    var box = $("#wz-slots"); box.innerHTML = "";
    if (!choix.jour) return;
    slotsFor(parse(choix.jour)).forEach(function (s) {
      var b = document.createElement("button"); b.type = "button"; b.className = "slot"; b.setAttribute("role", "option");
      b.textContent = hm(s.m); b.dataset.m = s.m; b.disabled = s.off; b.setAttribute("aria-selected", choix.heure === s.m);
      box.appendChild(b);
    });
  }
  $("#wz-days").addEventListener("click", function (e) {
    var b = e.target.closest(".day"); if (!b) return;
    choix.jour = b.dataset.iso; choix.heure = null;
    $$(".day").forEach(function (x) { x.setAttribute("aria-selected", x === b); }); renderSlots();
  });
  $("#wz-slots").addEventListener("click", function (e) {
    var b = e.target.closest(".slot"); if (!b || b.disabled) return;
    choix.heure = +b.dataset.m; $$(".slot").forEach(function (x) { x.setAttribute("aria-selected", x === b); });
  });

  function show(p) {
    page = p;
    $$(".wz-page", wiz).forEach(function (f) { f.hidden = +f.dataset.page !== p; });
    $$(".wz-steps li", wiz).forEach(function (li, i) { li.className = i === p ? "on" : i < p ? "done" : ""; });
    $("#wz-prev").hidden = p === 0;
    $("#wz-next").textContent = p === 2 ? "Préparer ma demande" : "Continuer";
    $("#wz-err").textContent = "";
    if (p === 2) renderDays();
  }
  function err(msg, el) { $("#wz-err").textContent = msg; if (el) { el.setAttribute("aria-invalid", "true"); el.focus(); } return false; }
  function valide() {
    $$("[aria-invalid]", wiz).forEach(function (x) { x.removeAttribute("aria-invalid"); });
    if (page === 0) {
      if (!$$(".chip[aria-pressed=true]").length && !$("#wz-desc").value.trim()) return err("Choisissez au moins un type de travaux ou décrivez le problème.");
    }
    if (page === 1) {
      var pl = $("#wz-plaque");
      if (pl.value && !plaqueOK(pl.value)) return err("L'immatriculation semble incomplète (exemple : AB-123-CD).", pl);
      if (!pl.value && !$("#wz-marque").value.trim() && typeVal() !== "vehicule") return err("Indiquez au moins l'immatriculation ou la marque du véhicule.", pl);
    }
    if (page === 2) {
      if (typeVal() !== "vehicule" && choix.heure == null) return err("Choisissez une heure de dépôt.");
      if (!$("#wz-nom").value.trim()) return err("Indiquez votre nom.", $("#wz-nom"));
      var tel = $("#wz-tel").value.replace(/[\s.\-]/g, "");
      if (!/^(\+33|0033|0)[1-9]\d{8}$/.test(tel)) return err("Le numéro de téléphone doit compter 10 chiffres (exemple : 06 12 34 56 78).", $("#wz-tel"));
      var m = $("#wz-mail").value.trim();
      if (m && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(m)) return err("L'adresse e-mail n'est pas valide.", $("#wz-mail"));
      if (!$("#wz-rgpd").checked) return err("Cochez la case d'accord pour que nous puissions vous recontacter.", $("#wz-rgpd"));
    }
    return true;
  }
  $("#wz-next").addEventListener("click", function () { if (!valide()) return; if (page < 2) show(page + 1); else recap(); });
  $("#wz-prev").addEventListener("click", function () { show(page - 1); });

  var LIB = { devis: "Demande de devis", rdv: "Demande de rendez-vous", sinistre: "Déclaration de sinistre", vehicule: "Demande véhicule d'occasion" };
  function recap() {
    var t = typeVal(), d = choix.jour ? parse(choix.jour) : null, v = function (s) { return $(s).value.trim(); };
    var lignes = [LIB[t] + " · AMKS Autos", ""];
    var tr = $$(".chip[aria-pressed=true]").map(function (b) { return b.textContent; });
    if (tr.length) lignes.push("Travaux : " + tr.join(", "));
    if (v("#wz-desc")) lignes.push("Détail : " + v("#wz-desc"));
    var veh = [v("#wz-marque"), v("#wz-modele")].filter(Boolean).join(" ");
    if (veh || v("#wz-plaque")) lignes.push("Véhicule : " + [veh, v("#wz-plaque")].filter(Boolean).join(" · ") + (v("#wz-km") ? " · " + (+v("#wz-km")).toLocaleString("fr-FR") + " km" : ""));
    if (t === "sinistre" && (v("#wz-assureur") || v("#wz-nsin"))) lignes.push("Assurance : " + [v("#wz-assureur"), v("#wz-nsin") && "sinistre n° " + v("#wz-nsin")].filter(Boolean).join(", "));
    if (d && choix.heure != null) lignes.push("Dépôt souhaité : " + JOURS[d.getDay()] + " " + frDate(d) + " à " + hm(choix.heure));
    lignes.push("", "Nom : " + v("#wz-nom"), "Téléphone : " + v("#wz-tel"));
    if (v("#wz-mail")) lignes.push("E-mail : " + v("#wz-mail"));
    var txt = lignes.join("\n");
    $("#recap-txt").textContent = txt;
    $("#send-wa").href = "https://wa.me/" + C.telephoneIntl + "?text=" + encodeURIComponent(txt);
    $("#send-mail").href = "mailto:" + C.email + "?subject=" + encodeURIComponent(LIB[t] + (v("#wz-plaque") ? " · " + v("#wz-plaque") : "")) + "&body=" + encodeURIComponent(txt);
    var ics = $("#send-ics");
    if (d && choix.heure != null) {
      var start = new Date(d); start.setHours(0, choix.heure, 0, 0);
      var f = function (x) { return iso(x).replace(/-/g, "") + "T" + pad(x.getHours()) + pad(x.getMinutes()) + "00"; };
      var end = new Date(start.getTime() + C.creneauMinutes * 6e4);
      var ev = ["BEGIN:VEVENT", "UID:" + f(start) + "-rdv@amks-autos", "DTSTAMP:" + new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+/, ""),
        "DTSTART:" + f(start), "DTEND:" + f(end), "SUMMARY:Dépôt du véhicule chez AMKS Autos (à confirmer par le garage)", "LOCATION:" + adresse.replace(/,/g, "\\,"),
        "DESCRIPTION:" + txt.replace(/\n/g, "\\n").replace(/,/g, "\\,"), "END:VEVENT"].join("\r\n");
      download("rdv-amks-autos.ics", icsFile([ev]), ics); ics.hidden = false;
    } else ics.hidden = true;
    wiz.hidden = true; $("#recap").hidden = false;
    $("#recap").scrollIntoView({ block: "start" });
  }
  $("#send-copy").addEventListener("click", function () {
    var txt = $("#recap-txt").textContent;
    var done = function () { toast("Texte copié. Collez-le dans un SMS ou un e-mail."); };
    var fallback = function () { var r = document.createRange(); r.selectNodeContents($("#recap-txt")); var s = getSelection(); s.removeAllRanges(); s.addRange(r); toast("Texte sélectionné : copiez-le avec Ctrl+C."); };
    if (navigator.clipboard) navigator.clipboard.writeText(txt).then(done, fallback); else fallback();
  });
  $("#send-wa").addEventListener("click", function () { toast("WhatsApp s'ouvre avec votre message : appuyez sur Envoyer."); });
  $("#recap-edit").addEventListener("click", function () { $("#recap").hidden = true; wiz.hidden = false; show(0); });

  function openWizard(type, travail) {
    var r = $("input[name=type][value=" + type + "]", wiz); if (r) r.checked = true;
    $("#recap").hidden = true; wiz.hidden = false;
    renderChips(travail); show(0);
    $("#demande").scrollIntoView({ block: "start" });
  }
  $$("[data-type]").forEach(function (a) {
    a.addEventListener("click", function (e) { e.preventDefault(); openWizard(a.dataset.type); });
  });
  renderChips(); show(0);
})();
