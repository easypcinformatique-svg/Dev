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
const PROMPT = `Tu es un assistant de gestion documentaire.
Analyse ce document scanne et genere exactement un nom de fichier.

REGLES STRICTES :
- Format : AAAA-MM-JJ_Type_Emetteur_Detail.pdf
- Max 80 caracteres total
- Pas d'espaces : remplace par des tirets
- Pas d'accents (e->e, e->e, c->c, etc.)
- Pas de caracteres speciaux sauf _ et - et EUR
- Tout en minuscules sauf la premiere lettre de chaque segment

TYPES DE DOCUMENTS (utilise exactement ces valeurs) :
Facture / Devis / Contrat / Releve / Avis / Courrier / Bulletin / Attestation / Acte / Quittance / Rapport / Autre

LOGIQUE DE NOMMAGE :
1. DATE : prends la date du document (pas la date d'aujourd'hui). Si absente, utilise 0000-00-00
2. TYPE : identifie parmi la liste ci-dessus
3. EMETTEUR : nom court de l'entreprise/organisme emetteur (max 20 caracteres, abrege si besoin)
4. DETAIL : montant TTC si facture/devis (ex: 1250EUR), ou mot-cle si autre type (ex: Resiliation, Avenant, Solde)

Exemples valides :
2026-03-28_Facture_EDF_312EUR.pdf
2026-01-15_Contrat_ELCR-Maconnerie_Travaux.pdf
2026-02-01_Releve_BNP_Fevrier2026.pdf
2025-12-10_Avis_Impots_Taxe-Fonciere.pdf
2026-03-05_Devis_Plombier-Martin_850EUR.pdf
0000-00-00_Courrier_Mairie_Urbanisme.pdf

Reponds UNIQUEMENT avec le nom du fichier.
Aucune explication. Aucun guillemet. Aucun point avant .pdf.`;

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
  ScriptApp.newTrigger("processNewScans")
    .timeDriven()
    .everyMinutes(10)
    .create();

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
  const sourceFolder = DriveApp.getFolderById(CONFIG.SOURCE_FOLDER_ID);
  const destFolder = DriveApp.getFolderById(CONFIG.DEST_FOLDER_ID);
  const files = sourceFolder.getFiles();

  while (files.hasNext()) {
    const file = files.next();
    const mimeType = file.getMimeType();

    // Traiter uniquement les PDF et images
    if (!mimeType.includes("pdf") && !mimeType.includes("image")) {
      continue;
    }

    try {
      const newName = analyzeWithGemini(file);

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
      logToSheet(file, "ERREUR: " + error.message, "Erreur");
      Logger.log("Erreur: " + error.message);
    }
  }
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
    let name = json.candidates[0].content.parts[0].text.trim();
    // Nettoyer les guillemets ou espaces parasites
    name = name.replace(/["`]/g, "").trim();
    // S'assurer que ca finit par .pdf
    if (!name.endsWith(".pdf")) {
      name = name + ".pdf";
    }
    return name;
  }

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
