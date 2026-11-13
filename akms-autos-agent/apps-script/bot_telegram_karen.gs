/**
 * AMKS AUTOS – Bot Telegram « questions à Karen »
 *
 * Chaque jour, envoie à Karen les questions ouvertes de l'onglet « Priorités »
 * (les plus lourdes en TVA d'abord) et les factures KAMS à arbitrer (boutons KAMS / AMKS).
 * Karen répond en faisant « Répondre » sur le message : texte, photo ou PDF.
 * Le bot range les pièces dans le Drive, écrit la réponse dans le Google Sheet
 * et prévient le responsable (Robert) en cas de problème.
 *
 * Aucun serveur : relevé des messages toutes les minutes par un déclencheur Apps Script.
 * Installation : voir INSTALLATION_BOT_TELEGRAM.md.
 */

const SHEET_ID = '1vaTvbh17MpS2U3fXxRS_KGCFO6gXdfTOcN7VIQ39Nu4';
const ONGLET_Q = 'Priorités';            // A Rang … J Réf. | K Réponse | L Statut
const ONGLET_K = 'Factures KAMS 2024';   // A N° … K Qui a fait le travail | L Commentaire
const PAR_JOUR = 3;                      // questions « Priorités » par envoi
const KAMS_PAR_JOUR = 5;                 // factures KAMS par envoi
const HEURE_ENVOI = 9;
const HEURE_RELANCE = 18;
const RELANCE_H = 48;                    // délai avant rappel puis alerte
const DOSSIER = 'Réponses Karen (Telegram)';
const TZ = 'Europe/Paris';
const IGNORER = ['Q20a'];                // répondue via l'onglet Factures KAMS 2024

const P = PropertiesService.getScriptProperties();

/* ------------------------------------------------------------------ Telegram */

function tg_(methode, donnees) {
  const r = UrlFetchApp.fetch('https://api.telegram.org/bot' + P.getProperty('TG_TOKEN') + '/' + methode, {
    method: 'post', contentType: 'application/json',
    payload: JSON.stringify(donnees || {}), muteHttpExceptions: true,
  });
  const j = JSON.parse(r.getContentText());
  if (!j.ok) console.warn(methode, r.getContentText());
  return j.ok ? j.result : null;
}

function esc_(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function envoyer_(chat, html, boutons, repondreA) {
  const p = { chat_id: chat, text: html, parse_mode: 'HTML', disable_web_page_preview: true };
  if (boutons) p.reply_markup = { inline_keyboard: boutons };
  if (repondreA) p.reply_parameters = { message_id: repondreA, allow_sending_without_reply: true };
  return tg_('sendMessage', p);
}

const admin_ = () => P.getProperty('ADMIN_CHAT');
const karen_ = () => P.getProperty('KAREN_CHAT');
function alerte_(html) { if (admin_()) envoyer_(admin_(), '⚠️ ' + html); }
const maintenant_ = (f) => Utilities.formatDate(new Date(), TZ, f || 'dd/MM HH:mm');

/* ------------------------------------------------------------ Relevé (1 min) */

function relever() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(5000)) return;
  try {
    const offset = Number(P.getProperty('OFFSET') || 0);
    const maj = tg_('getUpdates', { offset: offset, timeout: 0, allowed_updates: ['message', 'callback_query'] }) || [];
    maj.forEach(function (u) {
      P.setProperty('OFFSET', String(u.update_id + 1)); // jamais traité deux fois
      try { traiter_(u); } catch (e) { console.error(e); alerte_('Erreur du bot : ' + esc_(e.message)); }
    });
  } finally { lock.releaseLock(); }
}

function traiter_(u) {
  if (u.callback_query) return bouton_(u.callback_query);
  const m = u.message;
  if (!m) return;
  const chat = String(m.chat.id);
  const txt = (m.text || m.caption || '').trim();

  if (/^\/moi\b/.test(txt)) {                       // enregistrement du responsable
    const code = txt.split(/\s+/)[1];
    if (code && code === P.getProperty('CODE')) {
      P.setProperty('ADMIN_CHAT', chat);
      envoyer_(chat, '✅ Vous êtes enregistré comme responsable.\nDemandez à Karen d\'ouvrir le bot et d\'appuyer sur « Démarrer » (/start).\nCommandes : /etat, /envoyer, /pause, /reprise.');
    } else envoyer_(chat, 'Code incorrect.');
    return;
  }

  if (chat !== admin_() && chat !== karen_()) {      // inconnu : validation par le responsable
    if (/^\/start/.test(txt) && admin_()) {
      envoyer_(chat, 'Bonjour ! Votre accès est en cours de validation.');
      const nom = [m.from.first_name, m.from.last_name].filter(String).join(' ');
      envoyer_(admin_(), 'Nouvelle personne sur le bot : <b>' + esc_(nom) + '</b> (@' + esc_(m.from.username || '-') + '). Est-ce Karen ?',
        [[{ text: 'Oui, c\'est Karen', callback_data: 'karen|' + chat }, { text: 'Non', callback_data: 'refus|' + chat }]]);
    }
    return;
  }

  if (chat === admin_() && chat !== karen_()) return commandeAdmin_(txt);

  // --- Karen
  if (/^\/start/.test(txt)) return accueilKaren_();
  if (/^\/suite/.test(txt)) { if (!envoyerLot_(1, 1)) envoyer_(chat, 'Plus aucune question en attente, merci ! 🎉'); return; }

  const info = contenu_(m, txt);
  const qid = m.reply_to_message ? P.getProperty('m_' + m.reply_to_message.message_id) : null;
  if (qid) return enregistrer_(qid, info);

  // Pas de « Répondre » : on demande à quelle question cela correspond.
  const ouvertes = enCours_().slice(-8);
  if (!ouvertes.length) {
    alerte_('Message de Karen sans question en cours :\n' + esc_(info.txt || '(pièce jointe)'));
    P.setProperty('pend_' + m.message_id, JSON.stringify(info));
    return envoyer_(chat, 'Merci, c\'est transmis à Robert.');
  }
  P.setProperty('pend_' + m.message_id, JSON.stringify(info));
  envoyer_(chat, 'Merci ! C\'est pour quelle question ?',
    ouvertes.map(function (o) { return [{ text: o.lib.slice(0, 40), callback_data: 'a|' + m.message_id + '|' + o.mid }]; }),
    m.message_id);
}

function contenu_(m, txt) {
  const info = { txt: txt };
  if (m.photo && m.photo.length) info.file = { id: m.photo[m.photo.length - 1].file_id, name: '' };
  else if (m.document) info.file = { id: m.document.file_id, name: m.document.file_name || '' };
  return info;
}

/* ----------------------------------------------------------------- Boutons */

function bouton_(cb) {
  const d = cb.data || '', chat = String(cb.message.chat.id), mid = cb.message.message_id;
  tg_('answerCallbackQuery', { callback_query_id: cb.id });
  const retirerBoutons = function () { tg_('editMessageReplyMarkup', { chat_id: chat, message_id: mid, reply_markup: { inline_keyboard: [] } }); };

  if (chat === admin_() && /^(karen|refus)\|/.test(d)) {
    const cible = d.split('|')[1];
    retirerBoutons();
    if (d.indexOf('karen|') === 0) {
      P.setProperty('KAREN_CHAT', cible);
      envoyer_(admin_(), '✅ Karen est enregistrée. Premier envoi demain à ' + HEURE_ENVOI + ' h (ou tapez /envoyer).');
      accueilKaren_();
    } else envoyer_(cible, 'Accès refusé.');
    return;
  }
  if (chat !== karen_()) return;

  if (d.indexOf('a|') === 0) {                        // rattachement d'un message sans « Répondre »
    const parts = d.split('|'), info = JSON.parse(P.getProperty('pend_' + parts[1]) || 'null');
    const qid = P.getProperty('m_' + parts[2]);
    retirerBoutons();
    P.deleteProperty('pend_' + parts[1]);
    if (info && qid) enregistrer_(qid, info);
    return;
  }

  const qid = P.getProperty('m_' + mid);
  if (!qid) return;
  if (d === 'nsp') { retirerBoutons(); return enregistrer_(qid, { txt: 'Ne sais pas', nsp: true }); }
  if (d === 'tard') {
    const s = JSON.parse(P.getProperty('s_' + qid) || 'null');
    if (s) { s.t = Date.now(); P.setProperty('s_' + qid, JSON.stringify(s)); }
    return envoyer_(chat, 'D\'accord, je vous la reposerai.', null, mid);
  }
  if (d.indexOf('k|') === 0) {                        // choix KAMS / AMKS
    retirerBoutons();
    return enregistrer_(qid, { choix: d.split('|')[1], txt: '' });
  }
}

/* ------------------------------------------------------- Écriture du Sheet */

function ligne_(sh, col, valeur) {
  const n = sh.getLastRow();
  if (n < 4) return 0;
  const v = sh.getRange(4, col, n - 3, 1).getDisplayValues();
  for (let i = 0; i < v.length; i++) if (String(v[i][0]).trim() === String(valeur)) return i + 4;
  return 0;
}

function enregistrer_(qid, info) {
  const type = qid.slice(0, 1), id = qid.slice(2);
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const s = JSON.parse(P.getProperty('s_' + qid) || '{}');
  const lib = s.lib || id;
  let lien = '';
  if (info.file) {
    try { lien = sauverFichier_(info.file, id); }
    catch (e) { alerte_('Pièce de Karen non enregistrée (' + esc_(lib) + ') : ' + esc_(e.message)); }
  }
  const ajout = '[' + maintenant_() + ' Telegram] ' + (info.txt || '') + (lien ? (info.txt ? ' – ' : '') + 'pièce : ' + lien : '');

  if (type === 'P') {
    const sh = ss.getSheetByName(ONGLET_Q), r = ligne_(sh, 10, id);
    if (!r) { alerte_('Réponse pour « ' + esc_(id) + ' » : question introuvable dans Priorités.\n' + esc_(ajout)); return; }
    const k = sh.getRange(r, 11), avant = k.getDisplayValue();
    k.setValue(avant ? avant + '\n' + ajout : ajout);
    const piecAttendue = /facture|pi[eè]ce|photo|relev|duplicata|talon|bordereau|carte grise|contrat/i.test(s.piece || '');
    sh.getRange(r, 12).setValue(info.nsp ? 'Ne sais pas' : (piecAttendue && !info.file ? 'En partie' : 'Répondu'));
  } else {
    const sh = ss.getSheetByName(ONGLET_K), r = ligne_(sh, 1, id);
    if (!r) { alerte_('Réponse pour la facture KAMS n° ' + esc_(id) + ' : ligne introuvable.'); return; }
    if (info.choix) sh.getRange(r, 11).setValue(info.choix);
    if (info.txt || lien) {
      const c = sh.getRange(r, 12), avant = c.getDisplayValue();
      c.setValue(avant ? avant + '\n' + ajout : ajout);
    }
  }

  P.deleteProperty('s_' + qid);
  P.setProperty('REP_JOUR', String(Number(P.getProperty('REP_JOUR') || 0) + 1));
  envoyer_(karen_(), '✅ Noté pour « ' + esc_(lib) + ' ». Merci !' + (enCours_().length ? '' : '\nTapez /suite pour la question suivante.'), null, s.mid);

  // Ce qui demande l'intervention du responsable
  if (info.nsp || info.choix === 'Ne sais pas') alerte_('Karen ne sait pas répondre : <b>' + esc_(lib) + '</b>. À reprendre avec elle ou avec Corexx.');
  else if (!info.choix && !info.file && (info.txt || '').length < 4) alerte_('Réponse très courte de Karen pour <b>' + esc_(lib) + '</b> : « ' + esc_(info.txt) + ' ». À vérifier.');
  else if (type === 'P' && /facture|pi[eè]ce|photo|relev|duplicata|talon|bordereau|carte grise/i.test(s.piece || '') && !info.file && !/envo|mail|joint|demand/i.test(info.txt || ''))
    alerte_('Karen a répondu sans pièce jointe pour <b>' + esc_(lib) + '</b> (attendu : ' + esc_(s.piece) + ') :\n« ' + esc_(info.txt) + ' »');
}

function sauverFichier_(f, id) {
  const g = tg_('getFile', { file_id: f.id });
  if (!g) throw new Error('fichier introuvable sur Telegram');
  const blob = UrlFetchApp.fetch('https://api.telegram.org/file/bot' + P.getProperty('TG_TOKEN') + '/' + g.file_path).getBlob();
  const ext = (g.file_path.match(/\.\w+$/) || [''])[0];
  const nom = maintenant_('yyyy-MM-dd_HHmm') + '_Karen_' + String(id).replace(/[\\/:*?"<>|]/g, '-') + '_' + (f.name || ('photo' + ext));
  return dossier_().createFile(blob.setName(nom)).getUrl();
}

function dossier_() {
  const id = P.getProperty('DOSSIER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) { /* recréé ci-dessous */ } }
  const it = DriveApp.getFoldersByName(DOSSIER);
  const d = it.hasNext() ? it.next() : DriveApp.createFolder(DOSSIER);
  P.setProperty('DOSSIER_ID', d.getId());
  return d;
}

/* ------------------------------------------------------------------ Envoi */

function enCours_() {
  const all = P.getProperties(), out = [];
  Object.keys(all).forEach(function (k) {
    if (k.indexOf('s_') === 0) { const s = JSON.parse(all[k]); s.qid = k.slice(2); out.push(s); }
  });
  return out.sort(function (a, b) { return a.t - b.t; });
}

function poser_(qid, html, boutons, lib, piece) {
  const r = envoyer_(karen_(), html, boutons);
  if (!r) return false;
  P.setProperty('m_' + r.message_id, qid);
  P.setProperty('s_' + qid, JSON.stringify({ mid: r.message_id, t: Date.now(), n: 0, lib: lib, piece: piece || '' }));
  return true;
}

function envoyerLot_(nQ, nK) {
  if (!karen_() || P.getProperty('PAUSE')) return 0;
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let envoyes = 0, q = 0, k = 0;

  const shQ = ss.getSheetByName(ONGLET_Q);
  const vQ = shQ.getRange(4, 1, Math.max(shQ.getLastRow() - 3, 1), 12).getDisplayValues();
  for (const r of vQ) {
    if (q >= nQ) break;
    const ref = r[9];
    if (!ref || IGNORER.indexOf(ref) >= 0 || !/^(À répondre)?$/.test(r[11]) || P.getProperty('s_P:' + ref)) continue;
    const html = '❓ <b>Question ' + esc_(r[0]) + ' – ' + esc_(r[2]) + '</b>\n'
      + (r[4] ? '💶 Montant : ' + esc_(r[4]) + ' · ' : '') + 'TVA en jeu ≈ ' + esc_(r[5] || '0 €') + '\n'
      + '⚠️ Pourquoi : ' + esc_(r[6]) + '\n'
      + '📎 À fournir : ' + esc_(r[7]) + '\n\n'
      + esc_(r[3]) + '\n\n'
      + '↩️ Faites « Répondre » sur ce message (texte, photo ou PDF).';
    if (poser_('P:' + ref, html, [[{ text: '❔ Je ne sais pas', callback_data: 'nsp' }, { text: '⏭ Plus tard', callback_data: 'tard' }]], r[2], r[7])) { q++; envoyes++; }
  }

  const shK = ss.getSheetByName(ONGLET_K);
  const vK = shK.getRange(4, 1, Math.max(shK.getLastRow() - 3, 1), 12).getDisplayValues();
  for (const r of vK) {
    if (k >= nK) break;
    if (!r[0] || r[10] || P.getProperty('s_K:' + r[0])) continue;
    const html = '🧾 <b>Facture KAMS ' + esc_(r[0]) + '/78</b> – ' + esc_(r[2]) + ' du ' + esc_(r[1]) + '\n'
      + 'Client : ' + esc_(r[3]) + (r[4] ? ' · véhicule ' + esc_(r[4]) : '') + '\n'
      + '💶 ' + esc_(r[5]) + ' TTC · TVA ≈ ' + esc_(r[6]) + '\n'
      + (r[8] ? 'ℹ️ ' + esc_(r[8]) + '\n' : '')
      + '\nQui a vraiment fait ce travail ?\n(Vous pouvez aussi « Répondre » avec un commentaire.)';
    const b = [[{ text: 'AMKS', callback_data: 'k|AMKS' }, { text: 'KAMS', callback_data: 'k|KAMS' }],
               [{ text: 'Les deux', callback_data: 'k|Les deux' }, { text: '❔ Ne sais pas', callback_data: 'k|Ne sais pas' }]];
    if (poser_('K:' + r[0], html, b, 'Facture KAMS ' + r[2] + ' ' + r[3])) { k++; envoyes++; }
  }
  return envoyes;
}

function accueilKaren_() {
  envoyer_(karen_(), 'Bonjour Karen 👋\nChaque matin, je vous envoie quelques questions pour finaliser la comptabilité d\'AMKS, '
    + 'les plus importantes d\'abord.\n\nPour répondre : appuyez longuement sur la question, puis « Répondre », et écrivez ou envoyez la photo / le PDF.\n'
    + 'Boutons « Je ne sais pas » et « Plus tard » si besoin.\nTapez /suite quand vous voulez la question suivante.');
}

/* ------------------------------------------------------------ Déclencheurs */

function quotidien() {
  P.setProperty('REP_JOUR', '0');
  if (!karen_() || P.getProperty('PAUSE')) return;
  const n = envoyerLot_(PAR_JOUR, KAMS_PAR_JOUR);
  if (n) envoyer_(karen_(), 'Voilà pour aujourd\'hui (' + n + ' questions). Merci Karen ! 🙏');
}

function relancer() {
  const limite = Date.now() - RELANCE_H * 3600 * 1000;
  const retards = [];
  enCours_().forEach(function (s) {
    if (s.t > limite) return;
    if (s.n === 0) {
      envoyer_(karen_(), '🔔 Petit rappel pour cette question, quand vous avez un moment.', null, s.mid);
      s.n = 1; s.t = Date.now();
      P.setProperty('s_' + s.qid, JSON.stringify(s));
    } else if (s.n === 1) {
      retards.push(s.lib);
      s.n = 2;
      P.setProperty('s_' + s.qid, JSON.stringify(s));
    }
  });
  if (retards.length) alerte_('Sans réponse de Karen depuis 4 jours malgré un rappel :\n• ' + retards.map(esc_).join('\n• '));
  if (admin_()) envoyer_(admin_(), '📊 Aujourd\'hui : ' + (P.getProperty('REP_JOUR') || 0) + ' réponse(s) de Karen, '
    + enCours_().length + ' question(s) en attente.' + (P.getProperty('PAUSE') ? ' (bot en pause)' : ''));
}

function commandeAdmin_(txt) {
  const c = txt.split(/\s+/)[0];
  if (c === '/pause') { P.setProperty('PAUSE', '1'); return envoyer_(admin_(), '⏸ Envois suspendus (/reprise pour relancer).'); }
  if (c === '/reprise') { P.deleteProperty('PAUSE'); return envoyer_(admin_(), '▶️ Envois repris.'); }
  if (c === '/envoyer') { const n = envoyerLot_(PAR_JOUR, KAMS_PAR_JOUR); return envoyer_(admin_(), n ? n + ' question(s) envoyée(s) à Karen.' : 'Rien envoyé (Karen non enregistrée, pause, ou tout est déjà posé).'); }
  if (c === '/etat') {
    const ss = SpreadsheetApp.openById(SHEET_ID);
    const shQ = ss.getSheetByName(ONGLET_Q), st = shQ.getRange(4, 12, Math.max(shQ.getLastRow() - 3, 1), 1).getDisplayValues().map(function (r) { return r[0]; }).filter(String);
    const cpt = {}; st.forEach(function (x) { cpt[x] = (cpt[x] || 0) + 1; });
    const shK = ss.getSheetByName(ONGLET_K), kv = shK.getRange(4, 11, Math.max(shK.getLastRow() - 3, 1), 1).getDisplayValues().filter(function (r) { return r[0]; }).length;
    return envoyer_(admin_(), '📊 <b>Priorités</b> : ' + Object.keys(cpt).map(function (x) { return x + ' ' + cpt[x]; }).join(' · ')
      + '\n🧾 <b>Factures KAMS</b> : ' + kv + ' / 78 tranchées\n⏳ En attente de Karen : ' + enCours_().length);
  }
  envoyer_(admin_(), 'Commandes : /etat, /envoyer, /pause, /reprise');
}

/* ------------------------------------------------------------ Installation */

function installer() {
  if (!P.getProperty('TG_TOKEN')) throw new Error('Ajoutez d\'abord la propriété TG_TOKEN (Paramètres du projet > Propriétés du script).');
  const moi = tg_('getMe');
  if (!moi) throw new Error('Jeton Telegram refusé : vérifiez TG_TOKEN.');
  tg_('deleteWebhook', {});
  if (!P.getProperty('CODE')) P.setProperty('CODE', String(Math.floor(1000 + Math.random() * 9000)));
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (['relever', 'quotidien', 'relancer'].indexOf(t.getHandlerFunction()) >= 0) ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('relever').timeBased().everyMinutes(1).create();
  ScriptApp.newTrigger('quotidien').timeBased().everyDays(1).atHour(HEURE_ENVOI).inTimezone(TZ).create();
  ScriptApp.newTrigger('relancer').timeBased().everyDays(1).atHour(HEURE_RELANCE).inTimezone(TZ).create();
  dossier_();
  console.log('Bot @' + moi.username + ' installé. Dans Telegram, ouvrez @' + moi.username + ' et envoyez : /moi ' + P.getProperty('CODE'));
}

function desinstaller() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  console.log('Déclencheurs supprimés : le bot est arrêté.');
}
