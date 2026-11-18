/**
 * AMKS AUTOS – création automatique de brouillons Gmail dans la boîte d'AMKS.
 *
 * Principe : Claude (ou Robert) ajoute une ligne dans l'onglet « Brouillons à créer »
 * du tableur « Journal import mails AMKS AUTOS ». Toutes les 15 minutes, ce script
 * crée le brouillon dans Gmail (compte amks.autos2308@gmail.com), en réponse au mail
 * d'origine si une recherche est indiquée, puis note le résultat sur la ligne.
 *
 * Il N'ENVOIE JAMAIS rien : il crée seulement des brouillons, que Karen relit et envoie.
 * À chaque passage, il recopie aussi les mails des 21 derniers jours (lecture seule) dans l'onglet « Boîte AMKS ».
 *
 * Installation (une seule fois, connecté avec le compte AMKS) :
 *   1. script.google.com > Nouveau projet > coller ce fichier > Enregistrer.
 *   2. Exécuter la fonction installer() et accepter les autorisations (Gmail + Sheets).
 *   C'est tout : le déclencheur toutes les 15 minutes est créé et une première passe est faite.
 */

const BA_SHEET_ID = '1vaTvbh17MpS2U3fXxRS_KGCFO6gXdfTOcN7VIQ39Nu4';
const BA_TAB = 'Brouillons à créer';
const BA_HEADERS = ['Statut', 'À', 'Cc', 'Objet', 'Message', 'Répondre au mail trouvé par (recherche Gmail, facultatif)', 'Demandé par', 'Résultat'];
const BA_NOM = 'AMKS AUTOS – Karen NIKOGHOSSIAN';

/** À exécuter une fois : crée l'onglet si besoin et le déclencheur toutes les 15 minutes. */
function installer() {
  ongletBrouillons_();
  ScriptApp.getProjectTriggers()
    .filter((t) => t.getHandlerFunction() === 'creerBrouillonsEnAttente')
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('creerBrouillonsEnAttente').timeBased().everyMinutes(15).create();
  creerBrouillonsEnAttente();
}

/** Lit les lignes « À créer » et crée les brouillons correspondants. */
function creerBrouillonsEnAttente() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) return; // une passe à la fois
  try {
    const sh = ongletBrouillons_();
    const last = sh.getLastRow();
    if (last < 2) return;
    const rows = sh.getRange(2, 1, last - 1, BA_HEADERS.length).getValues();
    rows.forEach((r, i) => {
      const statut = String(r[0]).trim().toLowerCase();
      if (statut !== 'à créer' && statut !== 'a creer' && statut !== 'à creer') return;
      const ligne = i + 2;
      const a = String(r[1]).trim(), cc = String(r[2]).trim(), objet = String(r[3]).trim(), corps = String(r[4]);
      const recherche = String(r[5]).trim();
      try {
        if (!corps.trim()) throw new Error('message vide');
        const adresses = (a + ',' + cc).split(/[,;\s]+/).filter(Boolean);
        if (!a && !recherche) throw new Error('destinataire manquant');
        adresses.forEach((x) => { if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(x)) throw new Error('adresse invalide : ' + x); });

        let draft = null, mode = '';
        if (recherche) {
          const fils = GmailApp.search(recherche, 0, 1);
          if (fils.length) {
            const msgs = fils[0].getMessages();
            const dernier = msgs[msgs.length - 1];
            const opts = { name: BA_NOM };
            if (cc) opts.cc = cc;
            draft = dernier.createDraftReply(corps, opts);
            mode = 'en réponse à « ' + fils[0].getFirstMessageSubject() + ' » (' + dernier.getFrom() + ')';
          }
        }
        if (!draft) {
          if (!a) throw new Error('mail d\'origine introuvable et aucun destinataire');
          const opts = { name: BA_NOM };
          if (cc) opts.cc = cc;
          draft = GmailApp.createDraft(a, objet || '(sans objet)', corps, opts);
          mode = recherche ? 'nouveau message (mail d\'origine introuvable)' : 'nouveau message';
        }
        sh.getRange(ligne, 1).setValue('Créé');
        sh.getRange(ligne, 8).setValue(Utilities.formatDate(new Date(), 'Europe/Paris', 'dd/MM/yyyy HH:mm')
          + ' · brouillon créé, ' + mode + ' · id ' + draft.getId() + ' · NON envoyé');
      } catch (e) {
        sh.getRange(ligne, 1).setValue('Erreur');
        sh.getRange(ligne, 8).setValue(Utilities.formatDate(new Date(), 'Europe/Paris', 'dd/MM/yyyy HH:mm') + ' · ' + e.message);
      }
    });
  } finally {
    try { copierBoiteAmks(); } catch (e) { console.error('copie boîte : ' + e.message); }
    lock.releaseLock();
  }
}

/**
 * Copie en lecture seule des mails des 21 derniers jours de la boîte AMKS dans l'onglet « Boîte AMKS »,
 * pour que Robert et Claude voient ce qui arrive et ce qui part, pièces jointes ou non.
 * Ne modifie rien dans Gmail : pas de lecture marquée, pas de déplacement, pas d'envoi.
 */
const BA_BOITE_TAB = 'Boîte AMKS';
const BA_BOITE_HEADERS = ['Date', 'Sens', 'De', 'À', 'Objet', 'Message (début)', 'Pièces jointes', 'Nb messages', 'Non lu', 'Lien'];

function copierBoiteAmks() {
  const ss = SpreadsheetApp.openById(BA_SHEET_ID);
  let sh = ss.getSheetByName(BA_BOITE_TAB);
  if (!sh) {
    sh = ss.insertSheet(BA_BOITE_TAB);
    sh.setFrozenRows(1);
  }
  const moi = 'amks.autos2308@gmail.com'; // pas de Session.getEffectiveUser() : éviterait une nouvelle autorisation
  const fils = GmailApp.search('newer_than:21d -category:promotions -category:social', 0, 150);
  const lignes = [];
  fils.forEach((f) => {
    const msgs = f.getMessages();
    const m = msgs[msgs.length - 1];
    const de = m.getFrom();
    const envoye = de.toLowerCase().indexOf(moi) !== -1;
    const corps = m.getPlainBody().replace(/\r/g, '').replace(/\n{3,}/g, '\n\n').slice(0, 1500);
    const pj = m.getAttachments({ includeInlineImages: false }).map((a) => a.getName()).join(', ');
    lignes.push([m.getDate(), envoye ? 'Envoyé' : 'Reçu', de, m.getTo(), f.getFirstMessageSubject(), corps, pj,
      msgs.length, f.isUnread() ? 'Oui' : '', 'https://mail.google.com/mail/u/0/#all/' + f.getId()]);
  });
  lignes.sort((a, b) => b[0] - a[0]);
  sh.clearContents();
  sh.getRange(1, 1, 1, BA_BOITE_HEADERS.length).setValues([BA_BOITE_HEADERS]).setFontWeight('bold');
  if (lignes.length) {
    sh.getRange(2, 1, lignes.length, BA_BOITE_HEADERS.length).setValues(lignes);
    sh.getRange(2, 1, lignes.length, 1).setNumberFormat('dd/MM/yyyy HH:mm');
  }
  sh.getRange(1, 12).setValue('Mis à jour le ' + Utilities.formatDate(new Date(), 'Europe/Paris', 'dd/MM/yyyy HH:mm'));
}

function ongletBrouillons_() {
  const ss = SpreadsheetApp.openById(BA_SHEET_ID);
  let sh = ss.getSheetByName(BA_TAB);
  if (!sh) {
    sh = ss.insertSheet(BA_TAB);
    sh.getRange(1, 1, 1, BA_HEADERS.length).setValues([BA_HEADERS]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}
