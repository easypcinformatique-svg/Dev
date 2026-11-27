/**
 * AMKS AUTOS – brouillons automatiques + copie de la boîte mail (lecture seule).
 *
 * 1. Toutes les 15 minutes : crée dans Gmail (compte amks.autos2308@gmail.com) les brouillons
 *    listés « À créer » dans l'onglet « Brouillons à créer » du tableur « Journal import mails AMKS AUTOS ».
 * 2. Toutes les heures : recopie les mails des 21 derniers jours dans l'onglet « Boîte AMKS ».
 *
 * Il N'ENVOIE JAMAIS rien et ne modifie rien dans Gmail (pas de lu/non lu, pas de déplacement).
 *
 * Installation (une seule fois, connecté avec le compte AMKS) :
 *   1. script.google.com > projet du script > remplacer tout le code par ce fichier > Enregistrer.
 *   2. Exécuter installer() et accepter les autorisations (Gmail + Sheets).
 *      Elle remplace les anciens déclencheurs par les deux nouveaux et fait une première passe.
 */

const BA_SHEET_ID = '1vaTvbh17MpS2U3fXxRS_KGCFO6gXdfTOcN7VIQ39Nu4';
const BA_TAB = 'Brouillons à créer';
const BA_HEADERS = ['Statut', 'À', 'Cc', 'Objet', 'Message', 'Répondre au mail trouvé par (recherche Gmail, facultatif)', 'Demandé par', 'Résultat'];
const BA_NOM = 'AMKS AUTOS – Karen NIKOGHOSSIAN';
const BA_MOI = 'amks.autos2308@gmail.com';
const BA_BOITE_TAB = 'Boîte AMKS';
const BA_BOITE_HEADERS = ['Date', 'Sens', 'De', 'À', 'Objet', 'Message (début)', 'Pièce jointe', 'Nb messages', 'Non lu', 'Lien'];
const BA_BOITE_JOURS = 21;
const BA_BOITE_MAX = 100;     // fils copiés au maximum
const BA_BOITE_EXTRAIT = 500; // caractères de message copiés

/** À exécuter une fois : (re)crée les deux déclencheurs et fait une première passe. */
function installer() {
  ongletBrouillons_();
  ScriptApp.getProjectTriggers()
    .filter((t) => ['creerBrouillonsEnAttente', 'copierBoiteAmks'].indexOf(t.getHandlerFunction()) !== -1)
    .forEach((t) => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('creerBrouillonsEnAttente').timeBased().everyMinutes(15).create();
  ScriptApp.newTrigger('copierBoiteAmks').timeBased().everyHours(1).create();
  creerBrouillonsEnAttente();
  copierBoiteAmks();
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
      // Statut posé AVANT la création : si le script plante ensuite, la ligne reste « En cours »
      // et ne sera pas recréée au passage suivant (pas de doublon).
      sh.getRange(ligne, 1).setValue('En cours');
      SpreadsheetApp.flush();
      const a = String(r[1]).trim(), cc = String(r[2]).trim(), objet = String(r[3]).trim(), corps = String(r[4]);
      const recherche = String(r[5]).trim();
      try {
        if (!corps.trim()) throw new Error('message vide');
        if (!a && !recherche) throw new Error('destinataire manquant');
        (a + ',' + cc).split(/[,;\s]+/).filter(Boolean).forEach((x) => {
          if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(x)) throw new Error('adresse invalide : ' + x);
        });
        const opts = { name: BA_NOM };
        if (cc) opts.cc = cc;

        let draft = null, mode = '';
        if (recherche) {
          const fils = GmailApp.search(recherche, 0, 1);
          if (fils.length) {
            // On répond au dernier message reçu d'un tiers, jamais à un message envoyé par AMKS.
            const recus = fils[0].getMessages().filter((m) => m.getFrom().toLowerCase().indexOf(BA_MOI) === -1);
            const cible = recus.length ? recus[recus.length - 1] : null;
            const expediteur = cible ? cible.getFrom().toLowerCase() : '';
            if (cible && (!a || expediteur.indexOf(a.toLowerCase()) !== -1)) {
              draft = cible.createDraftReply(corps, opts);
              mode = 'en réponse à « ' + fils[0].getFirstMessageSubject() + ' » (' + cible.getFrom() + ')';
            } else if (cible) {
              mode = 'nouveau message : le fil trouvé (« ' + fils[0].getFirstMessageSubject() + ' ») ne vient pas de ' + a;
            }
          }
        }
        if (!draft) {
          if (!a) throw new Error('mail d\'origine introuvable et aucun destinataire');
          draft = GmailApp.createDraft(a, objet || '(sans objet)', corps, opts);
          mode = mode || (recherche ? 'nouveau message (mail d\'origine introuvable)' : 'nouveau message');
        }
        sh.getRange(ligne, 1).setValue('Créé');
        sh.getRange(ligne, 8).setValue(horodatage_() + ' · brouillon créé, ' + mode + ' · id ' + draft.getId() + ' · NON envoyé');
      } catch (e) {
        sh.getRange(ligne, 1).setValue('Erreur');
        sh.getRange(ligne, 8).setValue(horodatage_() + ' · ' + e.message);
      }
    });
  } finally {
    lock.releaseLock();
  }
}

/**
 * Copie en lecture seule des mails récents de la boîte AMKS dans l'onglet « Boîte AMKS » (une fois par heure).
 * Économe en quota : 2 recherches + 1 lecture par fil, sans charger les pièces jointes.
 */
function copierBoiteAmks() {
  const ss = SpreadsheetApp.openById(BA_SHEET_ID);
  let sh = ss.getSheetByName(BA_BOITE_TAB);
  if (!sh) { sh = ss.insertSheet(BA_BOITE_TAB); sh.setFrozenRows(1); }
  const filtre = 'newer_than:' + BA_BOITE_JOURS + 'd -category:promotions -category:social';
  const fils = GmailApp.search(filtre, 0, BA_BOITE_MAX);
  const avecPJ = {};
  GmailApp.search(filtre + ' has:attachment', 0, BA_BOITE_MAX).forEach((f) => { avecPJ[f.getId()] = true; });
  const lignes = fils.map((f) => {
    const msgs = f.getMessages();
    const m = msgs[msgs.length - 1];
    const de = m.getFrom();
    const corps = m.getPlainBody().replace(/\r/g, '').replace(/\n{3,}/g, '\n\n').slice(0, BA_BOITE_EXTRAIT);
    return [m.getDate(), de.toLowerCase().indexOf(BA_MOI) !== -1 ? 'Envoyé' : 'Reçu', sur_(de), sur_(m.getTo()),
      sur_(f.getFirstMessageSubject()), sur_(corps), avecPJ[f.getId()] ? 'Oui' : '', msgs.length, f.isUnread() ? 'Oui' : '',
      'https://mail.google.com/mail/?authuser=' + BA_MOI + '#all/' + f.getId()];
  });
  lignes.sort((x, y) => y[0] - x[0]);
  sh.clearContents();
  sh.getRange(1, 1, 1, BA_BOITE_HEADERS.length).setValues([BA_BOITE_HEADERS]).setFontWeight('bold');
  if (lignes.length) {
    sh.getRange(2, 1, lignes.length, BA_BOITE_HEADERS.length).setValues(lignes);
    sh.getRange(2, 1, lignes.length, 1).setNumberFormat('dd/MM/yyyy HH:mm');
  }
  sh.getRange(1, 12).setValue('Mis à jour le ' + horodatage_());
}

/** Empêche qu'un texte venu d'un mail soit lu comme une formule par le tableur. */
function sur_(v) {
  const s = String(v == null ? '' : v);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function horodatage_() {
  return Utilities.formatDate(new Date(), 'Europe/Paris', 'dd/MM/yyyy HH:mm');
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
