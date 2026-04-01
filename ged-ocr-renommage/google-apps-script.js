/**
 * GED Automatique - OCR Google Drive + Nommage intelligent
 *
 * Utilise l'OCR integre de Google Drive (gratuit, illimite).
 * Pas besoin de cle API externe.
 *
 * Installation :
 * 1. Ouvrir le Google Sheets "Log_GED"
 * 2. Extensions > Apps Script
 * 3. Coller ce code
 * 4. Selectionner "setup" > Executer
 * 5. Autoriser les acces Google
 * C'est tout.
 */

// === CONFIGURATION ===
var CONFIG = {
  SOURCE_FOLDER_ID: "1DkY7c22I7RQ4DtPo8FMkoAyMpSCrVEnF",
  DEST_FOLDER_ID: "1SpW0Us4bcLyrnHSSxq4nxMkYF1eDoe_l",
  SPREADSHEET_ID: "1sGofzRvhgRKPrH__2fUVIHSI6U3W6X_Sc4jTFPe1iHk",
  SHEET_NAME: "Log_GED"
};

// === MOTS-CLES POUR DETECTION DU TYPE ===
var TYPE_KEYWORDS = {
  "Facture": ["facture", "invoice", "fact.", "n° facture", "numero facture", "montant ttc", "total ttc", "net a payer"],
  "Devis": ["devis", "estimation", "proposition commerciale", "offre de prix"],
  "Contrat": ["contrat", "convention", "accord", "conditions generales", "entre les soussignes"],
  "Releve": ["releve", "releve de compte", "releve bancaire", "solde crediteur", "solde debiteur", "vos operations"],
  "Avis": ["avis d'imposition", "avis d'impot", "taxe fonciere", "taxe habitation", "impot", "dgfip", "tresor public"],
  "Courrier": ["courrier", "madame monsieur", "objet :", "veuillez agreer", "cordialement", "recommande"],
  "Bulletin": ["bulletin de paie", "bulletin de salaire", "salaire net", "net a payer avant impot", "cotisations"],
  "Attestation": ["attestation", "certifie", "atteste que", "attestation de"],
  "Acte": ["acte de", "notaire", "acte authentique", "acte de vente"],
  "Quittance": ["quittance", "loyer", "quittance de loyer"],
  "Rapport": ["rapport", "bilan", "compte rendu", "analyse"]
};

// === EMETTEURS CONNUS (du plus specifique au plus generique) ===
var KNOWN_EMITTERS = [
  ["totalenergies", "TotalEnergies"], ["engie", "Engie"], ["edf", "EDF"],
  ["free mobile", "Free"], ["freebox", "Free"], ["free", "Free"],
  ["orange", "Orange"], ["sfr", "SFR"], ["bouygues telecom", "Bouygues"],
  ["credit agricole", "Credit-Agricole"], ["credit mutuel", "Credit-Mutuel"],
  ["bnp paribas", "BNP"], ["societe generale", "Societe-Generale"],
  ["la banque postale", "Banque-Postale"], ["caisse d'epargne", "Caisse-Epargne"],
  ["lcl", "LCL"], ["boursorama", "Boursorama"], ["fortuneo", "Fortuneo"],
  ["axa", "AXA"], ["maif", "MAIF"], ["macif", "MACIF"], ["matmut", "Matmut"],
  ["groupama", "Groupama"], ["allianz", "Allianz"], ["generali", "Generali"],
  ["urssaf", "URSSAF"], ["cpam", "CPAM"], ["ameli", "CPAM"],
  ["pole emploi", "Pole-Emploi"], ["france travail", "France-Travail"],
  ["caf", "CAF"], ["dgfip", "Impots"], ["tresor public", "Tresor-Public"],
  ["direction generale des finances", "Impots"],
  ["prefecture", "Prefecture"], ["mairie", "Mairie"],
  ["leroy merlin", "Leroy-Merlin"], ["castorama", "Castorama"],
  ["boulanger", "Boulanger"], ["darty", "Darty"], ["fnac", "Fnac"],
  ["amazon", "Amazon"], ["cdiscount", "Cdiscount"], ["ikea", "IKEA"],
  ["ovh", "OVH"], ["o2switch", "O2switch"], ["ionos", "Ionos"],
  ["google", "Google"], ["microsoft", "Microsoft"], ["apple", "Apple"],
  ["brother", "Brother"], ["bouygues", "Bouygues"]
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
  Logger.log("Setup termine. Le script s'execute toutes les 10 minutes.");
}

function setupSheet() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  }

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

    if (mimeType.indexOf("pdf") === -1 && mimeType.indexOf("image") === -1) {
      continue;
    }

    try {
      // OCR via Google Drive (convertir en Google Doc puis extraire le texte)
      var ocrText = extractTextFromFile(file);
      Logger.log("OCR pour " + file.getName() + ": " + ocrText.substring(0, 100));

      if (!ocrText || ocrText.length < 10) {
        logToSheet(file, "ERREUR: OCR vide ou trop court", "", "Erreur");
        Logger.log("OCR trop court pour: " + file.getName());
        count++;
        continue;
      }

      // Analyser le texte et generer le nom
      var newName = generateFilename(ocrText);
      Logger.log("Nom genere: " + newName);

      // Renommer et deplacer
      file.setName(newName);
      file.moveTo(destFolder);

      logToSheet(file, newName, ocrText.substring(0, 200), "Traite");
      Logger.log("Traite: " + newName);

    } catch (error) {
      logToSheet(file, "ERREUR: " + error.message, "", "Erreur");
      Logger.log("Erreur pour " + file.getName() + ": " + error.message);
    }

    count++;

    // Pause entre fichiers
    if (count < MAX_FILES) {
      Utilities.sleep(2000);
    }
  }

  Logger.log("Fichiers traites: " + count);
}

/**
 * Extrait le texte d'un fichier via OCR Google Drive
 */
function extractTextFromFile(file) {
  // Utiliser l'API Drive pour convertir en Google Doc (avec OCR)
  var resource = {
    title: "temp_ocr_" + file.getName(),
    mimeType: "application/vnd.google-apps.document"
  };

  var options = {
    ocr: true,
    ocrLanguage: "fr"
  };

  // Inserer le fichier comme Google Doc avec OCR
  var blob = file.getBlob();
  var docFile;

  // Essayer v2 (insert) puis v3 (create)
  try {
    docFile = Drive.Files.insert(resource, blob, options);
  } catch(e) {
    // Drive API v3
    var v3resource = { name: resource.title, mimeType: resource.mimeType };
    docFile = Drive.Files.create(v3resource, blob, { ocrLanguage: "fr", fields: "id" });
  }

  // Ouvrir le Google Doc et extraire le texte
  var doc = DocumentApp.openById(docFile.id);
  var text = doc.getBody().getText();

  // Supprimer le fichier temporaire
  DriveApp.getFileById(docFile.id).setTrashed(true);

  return text;
}

/**
 * Genere un nom de fichier a partir du texte OCR
 */
function generateFilename(text) {
  var textLower = text.toLowerCase();

  // 1. Trouver la date
  var date = extractDate(text);

  // 2. Trouver le type de document
  var docType = detectType(textLower);

  // 3. Trouver l'emetteur
  var emitter = detectEmitter(textLower);

  // 4. Trouver le detail (montant ou mot-cle)
  var detail = extractDetail(textLower, docType);

  // Construire le nom
  var name = date + "_" + docType + "_" + emitter;
  if (detail) {
    name = name + "_" + detail;
  }
  name = name + ".pdf";

  // Nettoyer
  name = removeAccents(name);
  name = name.replace(/ /g, "-");
  name = name.replace(/[^a-zA-Z0-9_\-\.EUR€]/g, "");

  // Limiter a 80 caracteres
  if (name.length > 80) {
    name = name.substring(0, 76) + ".pdf";
  }

  return name;
}

/**
 * Extrait une date du texte (formats FR courants)
 */
function extractDate(text) {
  // Format: JJ/MM/AAAA ou JJ-MM-AAAA ou JJ.MM.AAAA
  var match = text.match(/(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})/);
  if (match) {
    return match[3] + "-" + match[2] + "-" + match[1];
  }

  // Format: AAAA-MM-JJ
  match = text.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    return match[0];
  }

  // Format texte: "15 mars 2026"
  var mois = {
    "janvier": "01", "fevrier": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "decembre": "12",
    "février": "02", "août": "08", "décembre": "12"
  };

  var textLower = text.toLowerCase();
  for (var m in mois) {
    var regex = new RegExp("(\\d{1,2})\\s+" + m + "\\s+(\\d{4})");
    match = textLower.match(regex);
    if (match) {
      var jour = match[1].length === 1 ? "0" + match[1] : match[1];
      return match[2] + "-" + mois[m] + "-" + jour;
    }
  }

  return "0000-00-00";
}

/**
 * Detecte le type de document
 */
function detectType(textLower) {
  var bestType = "Autre";
  var bestScore = 0;

  for (var type in TYPE_KEYWORDS) {
    var keywords = TYPE_KEYWORDS[type];
    var score = 0;
    for (var i = 0; i < keywords.length; i++) {
      if (textLower.indexOf(keywords[i]) > -1) {
        score++;
      }
    }
    if (score > bestScore) {
      bestScore = score;
      bestType = type;
    }
  }

  return bestType;
}

/**
 * Detecte l'emetteur du document
 */
function detectEmitter(textLower) {
  // Chercher dans les emetteurs connus (tableau ordonne du plus specifique au plus generique)
  for (var e = 0; e < KNOWN_EMITTERS.length; e++) {
    if (textLower.indexOf(KNOWN_EMITTERS[e][0]) > -1) {
      return KNOWN_EMITTERS[e][1];
    }
  }

  // Tenter d'extraire un nom d'entreprise (apres "de:" ou en haut du document)
  var lines = textLower.split("\n");
  for (var i = 0; i < Math.min(lines.length, 5); i++) {
    var line = lines[i].trim();
    if (line.length > 2 && line.length < 30 && line.indexOf("@") === -1) {
      var cleaned = line.replace(/[^a-zA-Z0-9 \-]/g, "").trim();
      if (cleaned.length > 2 && cleaned.length < 25) {
        // Capitaliser
        cleaned = cleaned.split(" ").map(function(w) {
          return w.charAt(0).toUpperCase() + w.slice(1);
        }).join("-");
        return cleaned.substring(0, 20);
      }
    }
  }

  return "Inconnu";
}

/**
 * Extrait le detail (montant ou mot-cle)
 */
function extractDetail(textLower, docType) {
  // Si facture ou devis, chercher un montant
  if (docType === "Facture" || docType === "Devis" || docType === "Quittance") {
    // Chercher "total ttc", "net a payer", "montant ttc"
    var montantPatterns = [
      /(?:total\s*ttc|net\s*[aà]\s*payer|montant\s*ttc|montant\s*total)[:\s]*(\d[\d\s]*[,\.]\d{2})/i,
      /(\d[\d\s]*[,\.]\d{2})\s*(?:€|eur|euros)/i,
      /€\s*(\d[\d\s]*[,\.]\d{2})/i
    ];

    for (var i = 0; i < montantPatterns.length; i++) {
      var match = textLower.match(montantPatterns[i]);
      if (match) {
        var montant = match[1].replace(/\s/g, "").replace(",", ".").replace(/\.(\d{2})$/, "$1");
        // Reconvertir en entier si possible
        var num = parseFloat(match[1].replace(/\s/g, "").replace(",", "."));
        if (!isNaN(num)) {
          if (num === Math.floor(num)) {
            return Math.floor(num) + "EUR";
          }
          return num.toFixed(2).replace(".", ",") + "EUR";
        }
      }
    }
  }

  // Pour les avis, chercher le type d'impot
  if (docType === "Avis") {
    if (textLower.indexOf("taxe fonciere") > -1) return "Taxe-Fonciere";
    if (textLower.indexOf("taxe habitation") > -1) return "Taxe-Habitation";
    if (textLower.indexOf("impot sur le revenu") > -1) return "Impot-Revenu";
  }

  // Pour les bulletins de paie, chercher le mois
  if (docType === "Bulletin") {
    var moisNoms = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
      "juillet", "aout", "septembre", "octobre", "novembre", "decembre"];
    for (var j = 0; j < moisNoms.length; j++) {
      if (textLower.indexOf(moisNoms[j]) > -1) {
        return moisNoms[j].charAt(0).toUpperCase() + moisNoms[j].slice(1);
      }
    }
  }

  // Pour les releves, chercher le mois
  if (docType === "Releve") {
    var moisNoms2 = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
      "juillet", "aout", "septembre", "octobre", "novembre", "decembre"];
    for (var k = 0; k < moisNoms2.length; k++) {
      if (textLower.indexOf(moisNoms2[k]) > -1) {
        return moisNoms2[k].charAt(0).toUpperCase() + moisNoms2[k].slice(1);
      }
    }
  }

  return "";
}

/**
 * Supprime les accents
 */
function removeAccents(str) {
  var accents = "àâäéèêëïîôùûüçÀÂÄÉÈÊËÏÎÔÙÛÜÇ";
  var sans    = "aaaeeeeiiouuucAAAEEEEIIOUUUC";
  var result = "";
  for (var i = 0; i < str.length; i++) {
    var idx = accents.indexOf(str[i]);
    result += idx > -1 ? sans[idx] : str[i];
  }
  return result;
}

function logToSheet(file, newName, ocrText, statut) {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  var now = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd HH:mm");
  var sizeKo = Math.round(file.getSize() / 1024);
  var originalName = file.getName();

  sheet.appendRow([now, originalName, newName, sizeKo, ocrText, statut]);
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
