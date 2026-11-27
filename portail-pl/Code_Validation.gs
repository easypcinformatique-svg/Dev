/**
 * PORTAIL PL — Service de validation EXCLUSIVEMENT.
 * À installer dans un SECOND projet Apps Script indépendant (non partagé avec Julie).
 * Web app: Exécuter en tant que « Moi » / accessible à « Tout le monde ».
 * Le service ne commande JAMAIS directement le Shelly ; il ne renvoie que ALLOW ou DENY.
 */
const SHEET_ID='1yo7wxGTL28P_C0l7emcZRDn7Y-6XN7ljbNUOkW-DKAA';
const TZ='Europe/Paris';
const MAX_USERS=5;

// À exécuter une fois manuellement dans l'éditeur du compte propriétaire.
// Ne communiquez jamais la clé générée dans une conversation ni dans un document partagé.
function installerClePrivee() {
  const props=PropertiesService.getScriptProperties();
  if (props.getProperty('PORTAIL_TOKEN')) throw new Error('Clé déjà installée. Pas de régénération accidentelle.');
  const token=Utilities.getUuid().replace(/-/g,'')+Utilities.getUuid().replace(/-/g,'');
  props.setProperty('PORTAIL_TOKEN',token);
  console.log('Clé PRIVÉE à copier directement sur le Note9 (ne pas la partager) : '+token);
}
function revoquerEtRegenererCle() {
  const token=Utilities.getUuid().replace(/-/g,'')+Utilities.getUuid().replace(/-/g,'');
  PropertiesService.getScriptProperties().setProperty('PORTAIL_TOKEN',token);
  console.log('Nouvelle clé à mettre dans MacroDroid : '+token);
}
function normalizePhone_(value) {
  let s=String(value||'').replace(/[^0-9]/g,'');
  if(s.startsWith('00')) s=s.slice(2);
  if(s.startsWith('0')) s='33'+s.slice(1);
  return /^33[1-9]\d{8}$/.test(s)?'+'+s:'';
}
function iso_(value) {
  if(value instanceof Date && !isNaN(value.getTime()))return Utilities.formatDate(value,TZ,'yyyy-MM-dd');
  const v=String(value||'').trim();
  if(/^\d{4}-\d{2}-\d{2}$/.test(v)) return v;
  const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(v);
  return m?`${m[3]}-${m[2]}-${m[1]}`:'';
}
// Google Sheets convertit « 08:00 » en heure : on relit la valeur affichée (« 8:00:00 », « 08:00 »…).
function hhmm_(display) {
  const m=/^(\d{1,2}):(\d{2})/.exec(String(display||'').trim());
  return m?m[1].padStart(2,'0')+':'+m[2]:'';
}
function response_(txt) {return ContentService.createTextOutput(txt).setMimeType(ContentService.MimeType.TEXT);}
function audit_(sh,phone,result,detail) {
  try {
    const log=sh.getParent().getSheetByName('Journal');
    if(log)log.appendRow([new Date(),phone,result,detail]);
  }catch(e){} // Échec de journalisation ne doit jamais rendre une demande autorisée.
}
function doGet(){ return response_('DENY'); }
function doPost(e) {
  try {
    const body=JSON.parse(String(e?.postData?.contents||'{}'));
    const actual=String(body.token||'');
    const expected=PropertiesService.getScriptProperties().getProperty('PORTAIL_TOKEN');
    if(!expected || actual.length!==64 || actual!==expected) return response_('DENY');
    const phone=normalizePhone_(body.phone);
    if(!phone) return response_('DENY');
    const sh=SpreadsheetApp.openById(SHEET_ID).getSheetByName('Artisans');
    const range=sh.getRange(2,1,MAX_USERS,8);
    const rows=range.getValues(), shown=range.getDisplayValues();
    const date=Utilities.formatDate(new Date(),TZ,'yyyy-MM-dd');
    const time=Utilities.formatDate(new Date(),TZ,'HH:mm');
    let verdict='DENY', detail='non autorisé';
    for (let i=0;i<rows.length;i++) {
      const r=rows[i];
      if (normalizePhone_(r[1])!==phone) continue;
      const start=iso_(r[2]),end=iso_(r[3]);
      const from=hhmm_(shown[i][4]),to=hhmm_(shown[i][5]);
      if (String(r[6]).trim().toUpperCase()!=='OUI'){detail='désactivé';break;}
      if (!start || !end || date<start || date>end){detail='hors dates';break;}
      if (!from||!to||time<from||time>=to){detail='hors horaires';break;}
      const key='recent_'+Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,phone)).slice(0,30);
      const cache=CacheService.getScriptCache();
      if(cache.get(key)){detail='temporisation anti-doublon';break;}
      cache.put(key,'1',25);
      verdict='ALLOW';detail='accès autorisé';break;
    }
    audit_(sh,phone,verdict,detail);
    return response_(verdict);
  } catch(err) {
    return response_('DENY'); // aucune ouverture en cas de panne / erreur / time-out
  }
}
