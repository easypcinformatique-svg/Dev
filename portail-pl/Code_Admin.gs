/**
 * PORTAIL PL — Administration privée. À installer dans un projet Google Apps Script
 * lié à la feuille « Accès Portail PL — Autorisations artisans ».
 * Déploiement : Exécuter en tant que « Utilisateur accédant à l'application » ;
 * accès : « Toute personne disposant d'un compte Google ».
 * Ne PAS déployer ce projet en « Exécuter en tant que moi ».
 */
const CONFIG = Object.freeze({
  SHEET_ID: '1yo7wxGTL28P_C0l7emcZRDn7Y-6XN7ljbNUOkW-DKAA',
  DATA_SHEET: 'Artisans',
  LOG_SHEET: 'Journal',
  ADMIN_EMAILS: ['easypc.informatique@gmail.com', 'scognamiglio.julie@gmail.com'],
  MAX_ARTISANS: 5,
  TZ: 'Europe/Paris'
});

function authorizedEmail_() {
  const email = String(Session.getActiveUser().getEmail() || '').trim().toLowerCase();
  if (!email || !CONFIG.ADMIN_EMAILS.includes(email)) {
    throw new Error("Accès interdit : compte Google non autorisé. Vérifier le déploiement « Exécuter en tant qu'utilisateur ».");
  }
  return email;
}

function dataSheet_() {
  authorizedEmail_();
  return SpreadsheetApp.openById(CONFIG.SHEET_ID).getSheetByName(CONFIG.DATA_SHEET);
}

function doGet() {
  try {
    authorizedEmail_();
    return HtmlService.createTemplateFromFile('Index').evaluate()
      .setTitle('Portail PL — Gestion des accès')
      .addMetaTag('viewport','width=device-width,initial-scale=1,viewport-fit=cover');
  } catch (err) {
    return HtmlService.createHtmlOutput('<h2>Accès refusé</h2><p>Vous devez être connecté avec un compte administrateur autorisé.</p>');
  }
}

function isoDate_(value) {
  if (value instanceof Date && !isNaN(value.getTime())) return Utilities.formatDate(value, CONFIG.TZ, 'yyyy-MM-dd');
  if (typeof value === 'string') {
    const v = value.trim();
    if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
    const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(v);
    if (m) return `${m[3]}-${m[2]}-${m[1]}`;
  }
  return '';
}
function normalizePhone_(input) {
  let digits = String(input || '').replace(/[^0-9]/g, '');
  if (digits.startsWith('00')) digits = digits.slice(2);
  if (digits.startsWith('0')) digits = '33' + digits.slice(1);
  return /^33[1-9]\d{8}$/.test(digits) ? '+' + digits : '';
}
function isValidIso_(v) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const d = new Date(v + 'T12:00:00Z');
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0,10) === v;
}
function isValidTime_(v) { return /^([01]\d|2[0-3]):[0-5]\d$/.test(String(v || '')); }
function toDate_(v) { return new Date(v+'T12:00:00'); }

function getInitialState() {
  const sh = dataSheet_();
  const rows = sh.getRange(2,1,CONFIG.MAX_ARTISANS,8).getValues();
  return {
    email: authorizedEmail_(),
    users: rows.map((r,i) => ({
      slot:i, name:String(r[0]||''),phone:String(r[1]||''),
      start:isoDate_(r[2]),end:isoDate_(r[3]),
      from:String(r[4]||'08:00'),to:String(r[5]||'20:00'),
      active:String(r[6]||'NON').toUpperCase()==='OUI',
      notes:String(r[7]||'')
    }))
  };
}

function saveArtisan(record) {
  const sh = dataSheet_();
  const slot = Number(record && record.slot);
  if (!Number.isInteger(slot) || slot<0 || slot>=CONFIG.MAX_ARTISANS) throw new Error('Emplacement invalide.');
  const name = String(record.name||'').trim().slice(0,80);
  const phone = normalizePhone_(record.phone);
  const start = String(record.start||'');
  const end = String(record.end||'');
  const from = String(record.from||'');
  const to = String(record.to||'');
  const notes = String(record.notes||'').trim().slice(0,240);
  if (!name || !phone) throw new Error('Nom et numéro français valides obligatoires.');
  if (!isValidIso_(start) || !isValidIso_(end) || start>end) throw new Error('Dates invalides.');
  if (!isValidTime_(from) || !isValidTime_(to) || from>=to) throw new Error('Créneau horaire invalide.');
  const all = sh.getRange(2,2,CONFIG.MAX_ARTISANS,1).getDisplayValues();
  if (all.some((r,i)=>i!==slot && normalizePhone_(r[0])===phone)) throw new Error('Numéro déjà autorisé dans un autre emplacement.');
  const lock = LockService.getDocumentLock() || LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const values=[name,phone,toDate_(start),toDate_(end),from,to,record.active===true?'OUI':'NON',notes];
    const range=sh.getRange(slot+2,1,1,8);
    sh.getRange(slot+2,2).setNumberFormat('@');
    range.setValues([values]);
    sh.getRange(slot+2,3,1,2).setNumberFormat('dd/MM/yyyy');
  } finally { lock.releaseLock(); }
  return getInitialState();
}

function revokeArtisan(slot) {
  const sh=dataSheet_(); slot=Number(slot);
  if (!Number.isInteger(slot)||slot<0||slot>=CONFIG.MAX_ARTISANS) throw new Error('Emplacement invalide.');
  sh.getRange(slot+2,7).setValue('NON');
  return getInitialState();
}
function deleteArtisan(slot) {
  const sh=dataSheet_(); slot=Number(slot);
  if (!Number.isInteger(slot)||slot<0||slot>=CONFIG.MAX_ARTISANS) throw new Error('Emplacement invalide.');
  sh.getRange(slot+2,1,1,8).clearContent();
  sh.getRange(slot+2,5,1,3).setValues([['08:00','20:00','NON']]);
  return getInitialState();
}

function searchMyGoogleContacts(query) {
  authorizedEmail_();
  const q=String(query||'').trim();
  if(q.length < 2) return [];
  // Service avancé People v1 à activer dans Apps Script > Services.
  const result=People.People.searchContacts({query:q,pageSize:30,readMask:'names,phoneNumbers'});
  return (result.results||[]).flatMap(r=>{
    const p=r.person||{}, name=p.names?.[0]?.displayName||'';
    return (p.phoneNumbers||[]).map(v=>({name,phone:normalizePhone_(v.value)}));
  }).filter(v=>v.name && v.phone).slice(0,30);
}
function primeContactsSearch() {
  authorizedEmail_();
  try { People.People.searchContacts({query:'',pageSize:1,readMask:'names,phoneNumbers'}); } catch(e) {}
  return true;
}

function getRecentJournal() {
  authorizedEmail_();
  const sh=SpreadsheetApp.openById(CONFIG.SHEET_ID).getSheetByName(CONFIG.LOG_SHEET);
  const last=sh.getLastRow(); if(last<=1) return [];
  const start=Math.max(2,last-39), n=last-start+1;
  return sh.getRange(start,1,n,4).getValues().map(r=>({
    at:r[0] instanceof Date?Utilities.formatDate(r[0],CONFIG.TZ,'dd/MM HH:mm'):String(r[0]||''),
    phone:String(r[1]||''),result:String(r[2]||''),detail:String(r[3]||'')
  })).reverse();
}
