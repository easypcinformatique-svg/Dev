/**
 * GED Automatique - OCR Google Drive + Nommage intelligent
 * Pas besoin de cle API externe.
 */

var CONFIG = {
  SOURCE_FOLDER_ID: "1DkY7c22I7RQ4DtPo8FMkoAyMpSCrVEnF",
  DEST_FOLDER_ID: "1SpW0Us4bcLyrnHSSxq4nxMkYF1eDoe_l",
  SPREADSHEET_ID: "1sGofzRvhgRKPrH__2fUVIHSI6U3W6X_Sc4jTFPe1iHk",
  SHEET_NAME: "Log_GED"
};

var TYPE_KEYWORDS = {
  "Facture": ["facture", "invoice", "fact n", "fact.", "numero facture", "montant ttc", "total ttc", "net a payer", "facture n", "facture du", "doit"],
  "Devis": ["devis", "estimation", "proposition commerciale", "offre de prix", "devis n"],
  "Contrat": ["contrat", "convention", "conditions generales", "entre les soussignes", "bail", "contrat de"],
  "Releve": ["releve de compte", "releve bancaire", "releve mensuel", "vos operations", "releve n", "nouveau solde", "ancien solde", "date valeur"],
  "Avis": ["avis d imposition", "avis d impot", "taxe fonciere", "taxe habitation", "dgfip", "tresor public", "impot sur le revenu", "avis de situation", "direction generale des finances"],
  "Courrier": ["madame monsieur", "objet :", "veuillez agreer", "cordialement", "recommande", "a l attention de", "pli recommande"],
  "Bulletin": ["bulletin de paie", "bulletin de salaire", "salaire net", "net a payer avant impot", "cotisations", "salaire brut", "conges payes"],
  "Attestation": ["attestation", "certifie", "atteste que", "attestation de", "je soussigne"],
  "Acte": ["acte de", "notaire", "acte authentique", "acte de vente", "acte notarie"],
  "Quittance": ["quittance", "quittance de loyer", "loyer du mois"],
  "Rapport": ["rapport", "compte rendu", "rapport de", "proces verbal"]
};

// Emetteurs : [mot-cle normalise (sans accent, minuscule), nom affiche]
// Ordre : du plus specifique au plus generique
var KNOWN_EMITTERS = [
  // Syndics / Immobilier
  ["a bis syndic", "Abis-Syndic"], ["foncia", "Foncia"], ["nexity", "Nexity"],
  ["oralia", "Oralia"], ["citya", "Citya"], ["syndic", "Syndic"],
  // Energie
  ["totalenergies", "TotalEnergies"], ["engie", "Engie"], ["edf", "EDF"],
  ["direct energie", "Direct-Energie"], ["eni", "ENI"], ["vattenfall", "Vattenfall"],
  ["veolia", "Veolia"], ["suez", "Suez"], ["grdf", "GRDF"],
  // Telecom
  ["free mobile", "Free-Mobile"], ["freebox", "Free"],
  ["orange", "Orange"], ["sosh", "Sosh"], ["sfr", "SFR"], ["red by sfr", "RED-SFR"],
  ["bouygues telecom", "Bouygues-Telecom"], ["b&you", "BandYou"],
  // Banques (specifiques avant generiques)
  ["credit agricole", "Credit-Agricole"], ["credit mutuel", "Credit-Mutuel"],
  ["credit lyonnais", "LCL"], ["bnp paribas", "BNP"],
  ["societe generale", "Societe-Generale"], ["la banque postale", "Banque-Postale"],
  ["caisse d epargne", "Caisse-Epargne"], ["banque populaire", "Banque-Populaire"],
  ["cic", "CIC"], ["lcl", "LCL"], ["boursorama", "Boursorama"],
  ["fortuneo", "Fortuneo"], ["ing direct", "ING"], ["hello bank", "HelloBank"],
  ["monabanq", "Monabanq"], ["n26", "N26"], ["revolut", "Revolut"],
  // Assurances
  ["axa", "AXA"], ["maif", "MAIF"], ["macif", "MACIF"], ["matmut", "Matmut"],
  ["groupama", "Groupama"], ["allianz", "Allianz"], ["generali", "Generali"],
  ["mma", "MMA"], ["maaf", "MAAF"], ["gmf", "GMF"], ["pacifica", "Pacifica"],
  ["harmonie mutuelle", "Harmonie"], ["alan", "Alan"], ["luko", "Luko"],
  // Sante
  ["cpam", "CPAM"], ["ameli", "CPAM"], ["mgen", "MGEN"],
  ["mutuelle", "Mutuelle"], ["harmonie", "Harmonie"],
  // Organismes publics
  ["urssaf", "URSSAF"], ["pole emploi", "Pole-Emploi"],
  ["france travail", "France-Travail"], ["caf", "CAF"],
  ["dgfip", "Impots"], ["tresor public", "Tresor-Public"],
  ["direction generale des finances", "Impots"], ["impots.gouv", "Impots"],
  ["service des impots", "Impots"],
  ["prefecture", "Prefecture"], ["sous-prefecture", "Sous-Prefecture"],
  ["mairie", "Mairie"], ["tribunal", "Tribunal"],
  ["securite sociale", "Secu"], ["carsat", "CARSAT"], ["cnav", "CNAV"],
  // Commerce / Grande distribution
  ["leroy merlin", "Leroy-Merlin"], ["castorama", "Castorama"],
  ["brico depot", "Brico-Depot"], ["mr bricolage", "MrBricolage"],
  ["boulanger", "Boulanger"], ["darty", "Darty"], ["fnac", "Fnac"],
  ["amazon", "Amazon"], ["cdiscount", "Cdiscount"], ["ikea", "IKEA"],
  ["but", "BUT"], ["conforama", "Conforama"], ["auchan", "Auchan"],
  ["carrefour", "Carrefour"], ["leclerc", "Leclerc"], ["lidl", "Lidl"],
  ["intermarche", "Intermarche"],
  // Auto
  ["norauto", "Norauto"], ["speedy", "Speedy"], ["midas", "Midas"],
  ["peugeot", "Peugeot"], ["renault", "Renault"], ["citroen", "Citroen"],
  // Tech / Hebergement
  ["ovh", "OVH"], ["o2switch", "O2switch"], ["ionos", "Ionos"],
  ["gandi", "Gandi"], ["scaleway", "Scaleway"],
  ["google", "Google"], ["microsoft", "Microsoft"], ["apple", "Apple"],
  ["adobe", "Adobe"], ["spotify", "Spotify"], ["netflix", "Netflix"],
  // BTP / Artisans
  ["plombier", "Plombier"], ["electricien", "Electricien"],
  ["maconnerie", "Maconnerie"], ["peintre", "Peintre"],
  // Divers
  ["la poste", "La-Poste"], ["chronopost", "Chronopost"], ["colissimo", "Colissimo"],
  ["brother", "Brother"], ["bouygues", "Bouygues"], ["free", "Free"],
  ["cleor", "Cleor"]
];

function setup() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  var builder = ScriptApp.newTrigger("processNewScans");
  var timeBuilder = builder.timeBased();
  timeBuilder.everyMinutes(10);
  timeBuilder.create();
  setupSheet();
  Logger.log("Setup termine. Le script s execute toutes les 10 minutes.");
}

function setupSheet() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  if (!sheet) { sheet = ss.insertSheet(CONFIG.SHEET_NAME); }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["Date traitement", "Nom original", "Nom final", "Taille (Ko)", "Texte OCR (extrait)", "Statut"]);
    sheet.getRange(1, 1, 1, 6).setFontWeight("bold");
  }
}

function processNewScans() {
  var sourceFolder = DriveApp.getFolderById(CONFIG.SOURCE_FOLDER_ID);
  var destFolder = DriveApp.getFolderById(CONFIG.DEST_FOLDER_ID);
  var files = sourceFolder.getFiles();
  var count = 0;
  var MAX_FILES = 5;
  while (files.hasNext() && count < MAX_FILES) {
    var file = files.next();
    var mimeType = file.getMimeType();
    if (mimeType.indexOf("pdf") === -1 && mimeType.indexOf("image") === -1) { continue; }
    try {
      var ocrText = extractTextFromFile(file);
      Logger.log("OCR pour " + file.getName() + ": " + ocrText.substring(0, 150));
      if (!ocrText || ocrText.length < 10) {
        logToSheet(file, "ERREUR: OCR vide", "", "Erreur");
        count++;
        continue;
      }
      var newName = generateFilename(ocrText);
      Logger.log("Nom genere: " + newName);
      file.setName(newName);
      file.moveTo(destFolder);
      logToSheet(file, newName, ocrText.substring(0, 200), "Traite");
      Logger.log("Traite: " + newName);
    } catch (error) {
      logToSheet(file, "ERREUR: " + error.message, "", "Erreur");
      Logger.log("Erreur pour " + file.getName() + ": " + error.message);
    }
    count++;
    if (count < MAX_FILES) { Utilities.sleep(2000); }
  }
  Logger.log("Fichiers traites: " + count);
}

function extractTextFromFile(file) {
  var blob = file.getBlob();
  var resource = {
    title: "temp_ocr_" + file.getName(),
    mimeType: "application/vnd.google-apps.document"
  };
  var docFile;
  try {
    docFile = Drive.Files.insert(resource, blob, { ocr: true, ocrLanguage: "fr" });
  } catch(e) {
    var v3resource = { name: resource.title, mimeType: resource.mimeType };
    docFile = Drive.Files.create(v3resource, blob, { ocrLanguage: "fr", fields: "id" });
  }
  var doc = DocumentApp.openById(docFile.id);
  var text = doc.getBody().getText();
  DriveApp.getFileById(docFile.id).setTrashed(true);
  return text;
}

/**
 * Supprime tous les accents d'une chaine
 */
function removeAccents(str) {
  if (!str) return "";
  var from = "àâäãéèêëïîìôöòùûüçñÀÂÄÃÉÈÊËÏÎÌÔÖÒÙÛÜÇÑ";
  var to   = "aaaaeeeeiiioooouuucnAAAAEEEEIIIOOOUUUCN";
  var result = "";
  for (var i = 0; i < str.length; i++) {
    var idx = from.indexOf(str[i]);
    result += idx > -1 ? to[idx] : str[i];
  }
  return result;
}

/**
 * Normalise le texte : minuscules + sans accents
 * Applique UNE SEULE FOIS avant toute analyse
 */
function normalize(text) {
  return removeAccents(text).toLowerCase();
}

function generateFilename(text) {
  // Normaliser le texte une seule fois (minuscules + sans accents)
  var norm = normalize(text);
  var date = extractDate(text, norm);
  var docType = detectType(norm);
  var emitter = detectEmitter(norm);
  var detail = extractDetail(norm, docType);

  var name = date + "_" + docType + "_" + emitter;
  if (detail) { name = name + "_" + detail; }
  name = name + ".pdf";

  // Nettoyage final du nom
  name = removeAccents(name);
  name = name.replace(/ /g, "-");
  name = name.replace(/[^a-zA-Z0-9_\-\.EUR]/g, "");
  // Eviter les doubles tirets
  name = name.replace(/-+/g, "-");
  name = name.replace(/_-/g, "_");
  name = name.replace(/-_/g, "_");
  if (name.length > 80) { name = name.substring(0, 76) + ".pdf"; }
  return name;
}

/**
 * Extrait la date du document
 * Cherche dans l'ordre : JJ/MM/AAAA, AAAA-MM-JJ, "24 decembre 2021"
 */
function extractDate(originalText, norm) {
  // Format: JJ/MM/AAAA ou JJ-MM-AAAA ou JJ.MM.AAAA
  var match = originalText.match(/(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})/);
  if (match) {
    var d = parseInt(match[1]), m = parseInt(match[2]);
    // Si le jour > 12, c'est bien JJ/MM/AAAA
    // Si le mois > 12, c'est MM/JJ/AAAA (format US) -> inverser
    if (m > 12 && d <= 12) { var tmp = d; d = m; m = tmp; }
    if (m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      return match[3] + "-" + pad(m) + "-" + pad(d);
    }
  }

  // Format: AAAA-MM-JJ
  match = originalText.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (match) { return match[0]; }

  // Format texte: "24 decembre 2021" (sur le texte normalise sans accents)
  var moisMap = {
    "janvier": "01", "fevrier": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "decembre": "12"
  };
  for (var m2 in moisMap) {
    // Gere "24 decembre 2021" et aussi "vendredi 24 decembre 2021"
    var regex = new RegExp("(\\d{1,2})\\s+" + m2 + "\\s+(\\d{4})");
    match = norm.match(regex);
    if (match) {
      return match[2] + "-" + moisMap[m2] + "-" + pad(parseInt(match[1]));
    }
    // Gere aussi "decembre 2021" sans jour
    var regex2 = new RegExp(m2 + "\\s+(\\d{4})");
    match = norm.match(regex2);
    if (match) {
      return match[1] + "-" + moisMap[m2] + "-01";
    }
  }

  return "0000-00-00";
}

function pad(n) {
  return n < 10 ? "0" + n : "" + n;
}

/**
 * Detecte le type de document par mots-cles
 */
function detectType(norm) {
  var bestType = "Autre";
  var bestScore = 0;
  for (var type in TYPE_KEYWORDS) {
    var keywords = TYPE_KEYWORDS[type];
    var score = 0;
    for (var i = 0; i < keywords.length; i++) {
      if (norm.indexOf(keywords[i]) > -1) { score++; }
    }
    if (score > bestScore) { bestScore = score; bestType = type; }
  }
  return bestType;
}

/**
 * Detecte l'emetteur : d'abord dans l'en-tete, puis dans tout le texte
 */
function detectEmitter(norm) {
  var lines = norm.split("\n");

  // En-tete = 10 premieres lignes
  var header = "";
  for (var h = 0; h < Math.min(lines.length, 10); h++) {
    header += lines[h] + " ";
  }

  // Chercher d'abord dans l'en-tete
  for (var e = 0; e < KNOWN_EMITTERS.length; e++) {
    if (header.indexOf(KNOWN_EMITTERS[e][0]) > -1) {
      return KNOWN_EMITTERS[e][1];
    }
  }

  // Puis dans tout le texte
  for (var f = 0; f < KNOWN_EMITTERS.length; f++) {
    if (norm.indexOf(KNOWN_EMITTERS[f][0]) > -1) {
      return KNOWN_EMITTERS[f][1];
    }
  }

  // Dernier recours : premiere ligne significative comme nom
  for (var i = 0; i < Math.min(lines.length, 5); i++) {
    var line = lines[i].trim();
    if (line.length > 3 && line.length < 40 && line.indexOf("@") === -1 && line.indexOf("http") === -1) {
      var cleaned = line.replace(/[^a-zA-Z0-9 \-]/g, "").trim();
      if (cleaned.length > 3 && cleaned.length < 30) {
        var words = cleaned.split(" ");
        var result = "";
        for (var w = 0; w < Math.min(words.length, 3); w++) {
          if (w > 0) result += "-";
          result += words[w].charAt(0).toUpperCase() + words[w].slice(1);
        }
        return result.substring(0, 20);
      }
    }
  }
  return "Inconnu";
}

/**
 * Extrait un detail : montant TTC pour factures, mot-cle pour autres
 */
function extractDetail(norm, docType) {
  // Montant pour factures/devis/quittances
  if (docType === "Facture" || docType === "Devis" || docType === "Quittance") {
    var montant = extractMontant(norm);
    if (montant) return montant;
  }

  // Avis d'impot
  if (docType === "Avis") {
    if (norm.indexOf("taxe fonciere") > -1) return "Taxe-Fonciere";
    if (norm.indexOf("taxe habitation") > -1) return "Taxe-Habitation";
    if (norm.indexOf("impot sur le revenu") > -1) return "Impot-Revenu";
    if (norm.indexOf("cotisation fonciere") > -1) return "CFE";
  }

  // Bulletins et releves : chercher le mois
  if (docType === "Bulletin" || docType === "Releve") {
    var moisNoms = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
      "juillet", "aout", "septembre", "octobre", "novembre", "decembre"];
    for (var j = 0; j < moisNoms.length; j++) {
      if (norm.indexOf(moisNoms[j]) > -1) {
        // Chercher aussi l'annee apres le mois
        var regAnnee = new RegExp(moisNoms[j] + "\\s*(\\d{4})");
        var matchA = norm.match(regAnnee);
        if (matchA) {
          return moisNoms[j].charAt(0).toUpperCase() + moisNoms[j].slice(1) + matchA[1];
        }
        return moisNoms[j].charAt(0).toUpperCase() + moisNoms[j].slice(1);
      }
    }
  }

  // Contrat : type de contrat
  if (docType === "Contrat") {
    if (norm.indexOf("bail") > -1) return "Bail";
    if (norm.indexOf("travaux") > -1) return "Travaux";
    if (norm.indexOf("assurance") > -1) return "Assurance";
    if (norm.indexOf("maintenance") > -1) return "Maintenance";
  }

  // Attestation : type
  if (docType === "Attestation") {
    if (norm.indexOf("domicile") > -1) return "Domicile";
    if (norm.indexOf("assurance") > -1) return "Assurance";
    if (norm.indexOf("responsabilite civile") > -1) return "RC";
    if (norm.indexOf("travail") > -1) return "Travail";
    if (norm.indexOf("hebergement") > -1) return "Hebergement";
  }

  // Courrier : sujet
  if (docType === "Courrier") {
    if (norm.indexOf("resiliation") > -1) return "Resiliation";
    if (norm.indexOf("reclamation") > -1) return "Reclamation";
    if (norm.indexOf("mise en demeure") > -1) return "Mise-en-demeure";
    if (norm.indexOf("preavis") > -1) return "Preavis";
    if (norm.indexOf("convocation") > -1) return "Convocation";
  }

  return "";
}

/**
 * Extrait le montant principal du document
 */
function extractMontant(norm) {
  var patterns = [
    // "Total TTC : 1 234,56" ou "Net a payer : 1234,56"
    /(?:total\s*ttc|net\s*a\s*payer|montant\s*ttc|montant\s*total|montant\s*du|total\s*general)[:\s]*(\d[\d\s]*[,\.]\d{2})/,
    // "1 234,56 €" ou "1234,56 eur"
    /(\d[\d\s]*[,\.]\d{2})\s*(?:€|eur|euros)/,
    // "€ 1 234,56"
    /(?:€|eur)\s*(\d[\d\s]*[,\.]\d{2})/
  ];
  for (var i = 0; i < patterns.length; i++) {
    var match = norm.match(patterns[i]);
    if (match) {
      var cleaned = match[1].replace(/\s/g, "").replace(",", ".");
      var num = parseFloat(cleaned);
      if (!isNaN(num) && num > 0 && num < 1000000) {
        if (num === Math.floor(num)) { return Math.floor(num) + "EUR"; }
        return num.toFixed(2).replace(".", ",") + "EUR";
      }
    }
  }
  return "";
}

function logToSheet(file, newName, ocrText, statut) {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  var now = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd HH:mm");
  var sizeKo = Math.round(file.getSize() / 1024);
  sheet.appendRow([now, file.getName(), newName, sizeKo, ocrText, statut]);
}

function testOneFile() {
  var sourceFolder = DriveApp.getFolderById(CONFIG.SOURCE_FOLDER_ID);
  var files = sourceFolder.getFiles();
  if (files.hasNext()) {
    var file = files.next();
    Logger.log("Test avec: " + file.getName());
    var ocrText = extractTextFromFile(file);
    Logger.log("Texte OCR: " + ocrText.substring(0, 300));
    var newName = generateFilename(ocrText);
    Logger.log("Nom genere: " + newName);
  } else {
    Logger.log("Aucun fichier dans le dossier source.");
  }
}
