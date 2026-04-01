/**
 * GED Automatique - OCR + Renommage via Google Apps Script
 *
 * Surveille un dossier Google Drive, analyse les documents avec Gemini,
 * renomme et deplace les fichiers, log dans Google Sheets.
 *
 * Installation :
 * 1. Ouvrir le Google Sheets "Log_GED"
 * 2. Extensions > Apps Script
 * 3. Coller ce code
 * 4. Remplacer GEMINI_API_KEY par ta cle
 * 5. Cliquer "Executer" sur la fonction setup()
 * 6. Autoriser les acces Google
 * C'est tout. Le script tourne automatiquement toutes les 10 minutes.
 */

// === CONFIGURATION ===
const CONFIG = {
  GEMINI_API_KEY: "AIzaSyC1DZfSSnnqqCIqLf09ACNk9igsdGqkfwA",
  SOURCE_FOLDER_ID: "1DkY7c22I7RQ4DtPo8FMkoAyMpSCrVEnF",
  DEST_FOLDER_ID: "1SpW0Us4bcLyrnHSSxq4nxMkYF1eDoe_l",
  SPREADSHEET_ID: "1sGofzRvhgRKPrH__2fUVIHSI6U3W6X_Sc4jTFPe1iHk",
  SHEET_NAME: "Log_GED",
  GEMINI_MODEL: "gemini-2.0-flash"
};

// === PROMPT GEMINI ===
const PROMPT = `INSTRUCTION: Generate ONLY a filename. No explanation. No quotes.

FORMAT: YYYY-MM-DD_Type_Emetteur_Detail.pdf

RULES:
- YYYY-MM-DD = document date (use 0000-00-00 if missing)
- Type = one of: Facture, Devis, Contrat, Releve, Avis, Courrier, Bulletin, Attestation, Acte, Quittance, Rapport, Autre
- Emetteur = short company name (max 20 chars, no spaces use dashes)
- Detail = amount if invoice (ex: 312EUR) or keyword (ex: Resiliation)
- No accents, no spaces, no special chars except _ - EUR
- Max 80 characters total

EXAMPLES:
2026-03-28_Facture_EDF_312EUR.pdf
2026-01-15_Contrat_ELCR-Maconnerie_Travaux.pdf
2025-12-10_Avis_Impots_Taxe-Fonciere.pdf
0000-00-00_Courrier_Mairie_Urbanisme.pdf

OUTPUT FORMAT: Just the filename, nothing else. Example: 2026-03-28_Facture_EDF_312EUR.pdf`;

/**
 * Installation : cree le trigger automatique toutes les 10 minutes
 * Executer cette fonction UNE SEULE FOIS
 */
function setup() {
  // Supprimer les anciens triggers
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }

  // Creer le trigger toutes les 10 minutes
  var builder = ScriptApp.newTrigger("processNewScans");
  var timeBuilder = builder.timeBased();
  timeBuilder.everyMinutes(10);
  timeBuilder.create();

  // Verifier les en-tetes du Sheet
  setupSheet();

  Logger.log("Setup termine. Le script s'execute toutes les 10 minutes.");
}

/**
 * Cree les en-tetes dans le Google Sheets si absentes
 */
function setupSheet() {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      "Date traitement",
      "Nom original",
      "Nom final",
      "Taille (Ko)",
      "Statut"
    ]);
    sheet.getRange(1, 1, 1, 5).setFontWeight("bold");
  }
}

/**
 * Fonction principale : traite les nouveaux fichiers dans le dossier source
 */
function processNewScans() {
  var sourceFolder = DriveApp.getFolderById(CONFIG.SOURCE_FOLDER_ID);
  var destFolder = DriveApp.getFolderById(CONFIG.DEST_FOLDER_ID);
  var files = sourceFolder.getFiles();
  var count = 0;
  var MAX_FILES = 5; // Traiter max 5 fichiers par execution

  while (files.hasNext() && count < MAX_FILES) {
    var file = files.next();
    var mimeType = file.getMimeType();

    // Traiter uniquement les PDF et images
    if (!mimeType.includes("pdf") && !mimeType.includes("image")) {
      continue;
    }

    // Pause de 5 secondes entre chaque fichier pour respecter le quota
    if (count > 0) {
      Utilities.sleep(5000);
    }

    try {
      var newName = analyzeWithGemini(file);

      if (newName && newName.endsWith(".pdf")) {
        // Renommer le fichier
        file.setName(newName);

        // Deplacer vers le dossier destination
        file.moveTo(destFolder);

        // Logger dans Google Sheets
        logToSheet(file, newName, "Traite");

        Logger.log("Traite: " + newName);
      } else {
        logToSheet(file, "ERREUR: " + (newName || "reponse vide"), "Erreur");
        Logger.log("Erreur nommage pour: " + file.getName());
      }
    } catch (error) {
      // Si quota depasse, arreter immediatement
      if (error.message && error.message.indexOf("429") > -1) {
        Logger.log("Quota Gemini depasse. Arret. Reprendra dans 10 minutes.");
        return;
      }
      logToSheet(file, "ERREUR: " + error.message, "Erreur");
      Logger.log("Erreur: " + error.message);
    }

    count++;
  }

  Logger.log("Fichiers traites: " + count);
}

/**
 * Envoie le fichier a Gemini pour OCR + nommage
 */
function analyzeWithGemini(file) {
  const blob = file.getBlob();
  const base64Data = Utilities.base64Encode(blob.getBytes());
  const mimeType = file.getMimeType();

  const url = "https://generativelanguage.googleapis.com/v1beta/models/"
    + CONFIG.GEMINI_MODEL
    + ":generateContent?key="
    + CONFIG.GEMINI_API_KEY;

  const payload = {
    contents: [{
      parts: [
        {
          inlineData: {
            mimeType: mimeType,
            data: base64Data
          }
        },
        {
          text: PROMPT
        }
      ]
    }],
    generationConfig: {
      maxOutputTokens: 80,
      temperature: 0.1
    }
  };

  const options = {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  const json = JSON.parse(response.getContentText());

  if (json.candidates && json.candidates[0] && json.candidates[0].content) {
    var rawText = json.candidates[0].content.parts[0].text.trim();
    Logger.log("Reponse brute Gemini: " + rawText);

    // Nettoyer les guillemets, backticks, espaces
    var name = rawText.replace(/["`']/g, "").trim();

    // Extraire le nom de fichier si Gemini a ajoute du texte autour
    var match = name.match(/\d{4}-\d{2}-\d{2}_[A-Za-z][\w\-]*_[\w\-]+[\w\-€EUR]*\.pdf/);
    if (match) {
      return match[0];
    }

    // Si le format est presque bon (contient .pdf et des underscores)
    if (name.indexOf(".pdf") > -1 && name.indexOf("_") > -1) {
      // Garder seulement la partie avant et incluant .pdf
      var pdfIndex = name.indexOf(".pdf");
      name = name.substring(0, pdfIndex + 4);
      // Remplacer les espaces par des tirets
      name = name.replace(/ /g, "-");
      return name;
    }

    // Dernier recours : reformater la reponse en nom valide
    name = name.replace(/\.pdf$/i, "");
    name = name.replace(/ /g, "-");
    name = name.replace(/[^a-zA-Z0-9_\-]/g, "");
    if (name.length > 60) name = name.substring(0, 60);
    return "0000-00-00_Autre_" + name + ".pdf";
  }

  // Log erreur API
  Logger.log("Erreur API Gemini: " + response.getContentText().substring(0, 200));
  return null;
}

/**
 * Ajoute une ligne dans le Google Sheets
 */
function logToSheet(file, newName, statut) {
  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = ss.getSheetByName(CONFIG.SHEET_NAME);

  const now = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd HH:mm");
  const sizeKo = Math.round(file.getSize() / 1024);
  const originalName = file.getName();

  sheet.appendRow([
    now,
    originalName,
    newName,
    sizeKo,
    statut
  ]);
}

/**
 * Fonction de test : traite un seul fichier pour verifier que tout marche
 */
function testOneFile() {
  const sourceFolder = DriveApp.getFolderById(CONFIG.SOURCE_FOLDER_ID);
  const files = sourceFolder.getFiles();

  if (files.hasNext()) {
    const file = files.next();
    Logger.log("Test avec: " + file.getName());

    const newName = analyzeWithGemini(file);
    Logger.log("Nom genere: " + newName);
  } else {
    Logger.log("Aucun fichier dans le dossier source.");
  }
}
