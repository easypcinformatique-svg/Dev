/* Widget de chat AKMS AUTOS.
 * Integration sur n'importe quel site :
 *   <script src="https://VOTRE-SERVEUR/widget.js" defer></script>
 */
(function () {
  if (window.__akmsWidget) return;
  window.__akmsWidget = true;

  var script = document.currentScript;
  var API = (script && script.dataset.api) || (script ? new URL(script.src).origin : "");
  var COULEUR = (script && script.dataset.couleur) || "#c8102e";
  var OUVERT = script && script.dataset.ouvert === "true";

  function sid() {
    var k = "akms_session";
    try {
      var v = localStorage.getItem(k);
      if (!v) { v = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2)); localStorage.setItem(k, v); }
      return v;
    } catch (e) { return "anon-" + Date.now(); }
  }
  var SESSION = sid();

  var css = document.createElement("style");
  css.textContent = [
    ".akms-btn{position:fixed;right:20px;bottom:20px;width:60px;height:60px;border-radius:50%;border:0;background:" + COULEUR + ";color:#fff;font-size:28px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:2147483000}",
    ".akms-box{position:fixed;right:20px;bottom:92px;width:360px;max-width:calc(100vw - 32px);height:540px;max-height:calc(100vh - 120px);background:#fff;color:#1d1d1f;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.25);display:none;flex-direction:column;overflow:hidden;font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;z-index:2147483000}",
    ".akms-box.on{display:flex}",
    ".akms-head{background:" + COULEUR + ";color:#fff;padding:12px 14px;display:flex;align-items:center;gap:8px}",
    ".akms-head b{flex:1}.akms-head button{background:none;border:0;color:#fff;cursor:pointer;font-size:13px;opacity:.9}",
    ".akms-log{flex:1;overflow-y:auto;padding:12px;background:#f5f5f7}",
    ".akms-m{max-width:85%;margin:6px 0;padding:8px 11px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word}",
    ".akms-u{margin-left:auto;background:" + COULEUR + ";color:#fff;border-bottom-right-radius:4px}",
    ".akms-a{background:#fff;border:1px solid #e3e3e8;border-bottom-left-radius:4px}",
    ".akms-ok{background:#e8f7ee;border:1px solid #9bd3b0;font-size:13px}",
    ".akms-sugg{display:flex;flex-wrap:wrap;gap:6px;padding:0 12px 8px;background:#f5f5f7}",
    ".akms-sugg button{border:1px solid " + COULEUR + ";color:" + COULEUR + ";background:#fff;border-radius:16px;padding:4px 10px;font-size:13px;cursor:pointer}",
    ".akms-form{display:flex;border-top:1px solid #e3e3e8}",
    ".akms-form textarea{flex:1;border:0;padding:12px;resize:none;font:inherit;outline:none;height:48px}",
    ".akms-form button{border:0;background:#fff;color:" + COULEUR + ";font-weight:600;padding:0 16px;cursor:pointer}",
    ".akms-foot{font-size:11px;color:#6e6e73;text-align:center;padding:4px;background:#fff}"
  ].join("\n");
  document.head.appendChild(css);

  var btn = document.createElement("button");
  btn.className = "akms-btn"; btn.setAttribute("aria-label", "Discuter avec AKMS AUTOS"); btn.textContent = "💬";
  var box = document.createElement("div");
  box.className = "akms-box"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", "Assistant AKMS AUTOS");
  box.innerHTML =
    '<div class="akms-head"><b>AKMS AUTOS – Assistant</b><button type="button" data-act="reset">Nouvelle conversation</button><button type="button" data-act="close" aria-label="Fermer">✕</button></div>' +
    '<div class="akms-log" aria-live="polite"></div>' +
    '<div class="akms-sugg"></div>' +
    '<form class="akms-form"><textarea placeholder="Votre message…" aria-label="Votre message"></textarea><button type="submit">Envoyer</button></form>' +
    '<div class="akms-foot">Assistant IA – les rendez-vous sont confirmés par le garage.</div>';
  document.body.appendChild(btn);
  document.body.appendChild(box);

  var log = box.querySelector(".akms-log");
  var sugg = box.querySelector(".akms-sugg");
  var form = box.querySelector("form");
  var input = form.querySelector("textarea");
  var occupe = false;

  function bulle(texte, cls) {
    var d = document.createElement("div");
    d.className = "akms-m " + cls; d.textContent = texte;
    log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
  }
  function accueil() {
    log.textContent = "";
    bulle("Bonjour et bienvenue chez AKMS AUTOS ! Je peux vous aider à trouver un véhicule, prendre rendez-vous à l'atelier ou transmettre une demande de devis ou de reprise.", "akms-a");
    sugg.textContent = "";
    ["Voir les véhicules en vente", "Prendre RDV pour une vidange", "Faire estimer ma voiture", "Vos horaires ?"].forEach(function (t) {
      var b = document.createElement("button"); b.type = "button"; b.textContent = t;
      b.onclick = function () { envoyer(t); }; sugg.appendChild(b);
    });
  }
  function envoyer(texte) {
    texte = (texte || "").trim();
    if (!texte || occupe) return;
    occupe = true; sugg.textContent = "";
    bulle(texte, "akms-u"); input.value = "";
    var attente = bulle("…", "akms-a");
    fetch(API + "/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: SESSION, message: texte })
    }).then(function (r) {
      if (r.status === 429) return { reponse: "Vous envoyez beaucoup de messages : patientez une minute s'il vous plaît." };
      if (!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function (d) {
      attente.textContent = d.reponse;
      (d.actions || []).forEach(function (a) {
        var r = a.resultat || {};
        if (a.outil === "prendre_rendez_vous") bulle("✔ Rendez-vous n°" + r.numero_rdv + " enregistré (à confirmer par le garage)", "akms-ok");
        if (a.outil === "enregistrer_demande") bulle("✔ Demande n°" + r.numero_demande + " transmise à l'équipe", "akms-ok");
      });
    }).catch(function () {
      attente.textContent = "Connexion impossible pour le moment. Merci de réessayer ou d'appeler le garage.";
    }).finally(function () { occupe = false; input.focus(); });
  }

  btn.onclick = function () { box.classList.toggle("on"); if (box.classList.contains("on")) input.focus(); };
  box.querySelector('[data-act="close"]').onclick = function () { box.classList.remove("on"); };
  box.querySelector('[data-act="reset"]').onclick = function () {
    fetch(API + "/api/reset", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: SESSION, message: "" }) }).catch(function () {});
    try { localStorage.removeItem("akms_session"); } catch (e) {}
    SESSION = sid(); accueil();
  };
  form.onsubmit = function (e) { e.preventDefault(); envoyer(input.value); };
  input.addEventListener("keydown", function (e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); envoyer(input.value); } });

  accueil();
  if (OUVERT) box.classList.add("on");
})();
