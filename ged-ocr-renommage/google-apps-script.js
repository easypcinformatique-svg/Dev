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
  "Facture": ["facture", "invoice", "fact.", "fact n", "facture n", "facture du", "numero de facture", "montant ttc", "total ttc", "net a payer", "total ht", "montant ht", "tva", "echeance", "conditions de paiement", "en votre aimable reglement", "facture acquittee", "proforma", "avoir", "note de credit", "doit", "acompte", "arrete la presente facture", "duplicata", "abonnement", "redevance", "consommation", "detail des prestations", "main d oeuvre", "fournitures"],
  "Devis": ["devis", "devis estimatif", "devis descriptif", "estimation", "proposition commerciale", "offre de prix", "offre commerciale", "chiffrage", "devis n", "numero de devis", "validite du devis", "bon pour accord", "lu et approuve", "delai d execution", "delai de realisation", "acompte a la commande", "sans engagement", "prix ferme", "forfait"],
  "Contrat": ["contrat", "convention", "conditions generales", "entre les soussignes", "bail", "contrat de", "ci-apres denomme", "d une part", "d autre part", "il est convenu", "objet du contrat", "duree du contrat", "prise d effet", "resiliation", "tacite reconduction", "obligations", "avenant", "annexe", "conditions particulieres", "fait en double exemplaire", "paraphe"],
  "Releve": ["releve de compte", "releve bancaire", "releve mensuel", "extrait de compte", "solde precedent", "nouveau solde", "solde crediteur", "solde debiteur", "date de valeur", "date d operation", "vos operations", "total des debits", "total des credits", "virement", "prelevement", "prelevement sepa", "paiement carte", "paiement cb", "retrait dab", "agios", "frais bancaires", "arrete de compte"],
  "Avis": ["avis d imposition", "avis d impot", "taxe fonciere", "taxe d habitation", "dgfip", "tresor public", "impot sur le revenu", "direction generale des finances", "revenu fiscal de reference", "revenu net imposable", "nombre de parts", "taux d imposition", "prelevement a la source", "tiers provisionnel", "mensualisation", "centre des finances publiques", "numero fiscal", "date de mise en recouvrement", "cotisation fonciere", "cfe", "ifi", "contribution sociale"],
  "Courrier": ["madame monsieur", "objet :", "veuillez agreer", "cordialement", "recommande", "a l attention de", "pli recommande", "mise en demeure", "je soussigne", "j ai l honneur", "je vous prie de bien vouloir", "salutations distinguees", "dans l attente de votre reponse", "suite a votre courrier", "par la presente", "accuse de reception", "cachet de la poste", "piece jointe", "reclamation", "contestation", "notification", "convocation", "rappel", "relance", "sommation"],
  "Bulletin": ["bulletin de paie", "bulletin de salaire", "fiche de paie", "salaire brut", "salaire net", "net a payer", "net imposable", "net fiscal", "matricule", "numero de securite sociale", "convention collective", "coefficient", "taux horaire", "salaire de base", "heures supplementaires", "prime", "indemnite", "conges payes", "rtt", "cotisations salariales", "cotisations patronales", "urssaf", "retraite complementaire", "agirc", "arrco", "prevoyance", "mutuelle", "csg", "crds", "prelevement a la source", "cumul annuel", "cumul brut"],
  "Attestation": ["attestation", "certifie", "atteste que", "attestation de", "je soussigne", "declare sur l honneur", "attestation sur l honneur", "attestation de domicile", "attestation d hebergement", "attestation employeur", "attestation de travail", "attestation de salaire", "attestation de droits", "attestation d assurance", "attestation de responsabilite civile", "certificat", "certificat medical", "certificat de scolarite", "delivre pour servir et valoir", "fait pour servir et valoir"],
  "Acte": ["acte notarie", "acte authentique", "acte de vente", "acte de propriete", "acte de naissance", "acte de mariage", "acte de deces", "notaire", "office notarial", "etude notariale", "par devant", "maitre", "comparant", "minute", "grosse", "expedition", "publicite fonciere", "cadastre", "reference cadastrale", "copropriete", "compromis de vente", "promesse de vente", "diagnostics", "loi carrez", "donation", "succession", "testament"],
  "Quittance": ["quittance", "quittance de loyer", "recu de loyer", "loyer", "montant du loyer", "loyer principal", "charges locatives", "charges recuperables", "provision pour charges", "regularisation des charges", "bailleur", "proprietaire", "locataire", "preneur", "depot de garantie", "apl", "aide au logement", "taxe d ordures menageres", "pour acquit", "indice de reference des loyers", "irl", "loyer du mois"],
  "Rapport": ["rapport", "compte rendu", "proces-verbal", "proces verbal", "rapport d activite", "rapport annuel", "rapport de gestion", "rapport d expertise", "rapport de mission", "rapport d audit", "rapport technique", "rapport de synthese", "introduction", "sommaire", "conclusions", "recommandations", "preconisations", "annexes", "diagnostic", "expertise", "inspection", "controle", "audit"]
};

var KNOWN_EMITTERS = [
  // Syndics / Immobilier
  ["a bis syndic", "Abis-Syndic"], ["foncia", "Foncia"], ["nexity", "Nexity"],
  ["oralia", "Oralia"], ["citya", "Citya"], ["lamy", "Lamy"], ["sergic", "Sergic"],
  ["immo de france", "Immo-de-France"], ["laforet", "Laforet"],
  ["century 21", "Century21"], ["guy hoquet", "Guy-Hoquet"], ["orpi", "Orpi"],
  ["stephane plaza", "Stephane-Plaza"], ["square habitat", "Square-Habitat"],
  ["paris habitat", "Paris-Habitat"], ["syndic", "Syndic"],
  // Energie
  ["totalenergies", "TotalEnergies"], ["engie", "Engie"], ["edf", "EDF"],
  ["direct energie", "Direct-Energie"], ["eni", "ENI"], ["vattenfall", "Vattenfall"],
  ["ekwateur", "Ekwateur"], ["ilek", "Ilek"], ["enercoop", "Enercoop"],
  ["veolia", "Veolia"], ["suez", "Suez"], ["grdf", "GRDF"], ["enedis", "Enedis"],
  ["antargaz", "Antargaz"], ["butagaz", "Butagaz"], ["primagaz", "Primagaz"],
  ["dalkia", "Dalkia"], ["saur", "Saur"],
  // Telecom
  ["free mobile", "Free-Mobile"], ["freebox", "Free"],
  ["orange", "Orange"], ["sosh", "Sosh"],
  ["sfr", "SFR"], ["red by sfr", "RED-SFR"],
  ["bouygues telecom", "Bouygues-Telecom"], ["b&you", "BandYou"],
  ["la poste mobile", "LaPoste-Mobile"], ["nrj mobile", "NRJ-Mobile"],
  ["prixtel", "Prixtel"], ["coriolis", "Coriolis"],
  ["nordnet", "Nordnet"], ["numericable", "Numericable"],
  // Banques
  ["credit agricole", "Credit-Agricole"], ["credit mutuel", "Credit-Mutuel"],
  ["credit lyonnais", "LCL"], ["credit cooperatif", "Credit-Cooperatif"],
  ["credit du nord", "Credit-du-Nord"],
  ["bnp paribas", "BNP"], ["societe generale", "Societe-Generale"],
  ["la banque postale", "Banque-Postale"], ["caisse d epargne", "Caisse-Epargne"],
  ["banque populaire", "Banque-Populaire"],
  ["cic", "CIC"], ["lcl", "LCL"], ["bred", "BRED"],
  ["boursorama", "Boursorama"], ["boursobank", "BoursoBank"],
  ["fortuneo", "Fortuneo"], ["ing direct", "ING"], ["hello bank", "HelloBank"],
  ["monabanq", "Monabanq"], ["n26", "N26"], ["revolut", "Revolut"],
  ["orange bank", "Orange-Bank"], ["ma french bank", "MaFrenchBank"],
  ["nickel", "Nickel"], ["bforbank", "BforBank"],
  ["banque palatine", "Banque-Palatine"], ["natixis", "Natixis"],
  ["arkea", "Arkea"], ["hsbc", "HSBC"],
  // Assurances
  ["axa", "AXA"], ["maif", "MAIF"], ["macif", "MACIF"], ["matmut", "Matmut"],
  ["groupama", "Groupama"], ["allianz", "Allianz"], ["generali", "Generali"],
  ["mma", "MMA"], ["maaf", "MAAF"], ["gmf", "GMF"], ["gan", "GAN"],
  ["pacifica", "Pacifica"], ["aviva", "Aviva"], ["swiss life", "Swiss-Life"],
  ["ag2r la mondiale", "AG2R"], ["malakoff humanis", "Malakoff-Humanis"],
  ["harmonie mutuelle", "Harmonie-Mutuelle"], ["alan", "Alan"], ["luko", "Luko"],
  ["direct assurance", "Direct-Assurance"], ["cnp assurances", "CNP"],
  ["covea", "Covea"], ["april", "April"],
  // Sante
  ["cpam", "CPAM"], ["ameli", "CPAM"], ["mgen", "MGEN"], ["mnh", "MNH"],
  ["uneo", "UNEO"], ["mutuelle", "Mutuelle"],
  // Organismes publics
  ["urssaf", "URSSAF"], ["pole emploi", "Pole-Emploi"],
  ["france travail", "France-Travail"], ["caf", "CAF"],
  ["dgfip", "Impots"], ["tresor public", "Tresor-Public"],
  ["direction generale des finances", "Impots"],
  ["impots.gouv", "Impots"], ["service des impots", "Impots"],
  ["centre des finances publiques", "Impots"],
  ["prefecture", "Prefecture"], ["sous-prefecture", "Sous-Prefecture"],
  ["mairie", "Mairie"], ["commune", "Mairie"],
  ["tribunal", "Tribunal"], ["greffe", "Greffe"],
  ["securite sociale", "Secu"], ["carsat", "CARSAT"], ["cnav", "CNAV"],
  ["agirc-arrco", "Agirc-Arrco"], ["ircantec", "Ircantec"],
  ["msa", "MSA"], ["ants", "ANTS"],
  ["education nationale", "Education-Nationale"], ["rectorat", "Rectorat"],
  ["crous", "CROUS"], ["mission locale", "Mission-Locale"],
  ["ars", "ARS"], ["ademe", "ADEME"], ["anah", "ANAH"],
  ["chambre de commerce", "CCI"], ["chambre des metiers", "CMA"],
  // Grande distribution
  ["leroy merlin", "Leroy-Merlin"], ["castorama", "Castorama"],
  ["brico depot", "Brico-Depot"], ["bricomarche", "Bricomarche"],
  ["mr bricolage", "MrBricolage"],
  ["boulanger", "Boulanger"], ["darty", "Darty"], ["fnac", "Fnac"],
  ["amazon", "Amazon"], ["cdiscount", "Cdiscount"], ["ikea", "IKEA"],
  ["but", "BUT"], ["conforama", "Conforama"],
  ["auchan", "Auchan"], ["carrefour", "Carrefour"], ["leclerc", "Leclerc"],
  ["lidl", "Lidl"], ["intermarche", "Intermarche"], ["casino", "Casino"],
  ["monoprix", "Monoprix"], ["picard", "Picard"],
  ["decathlon", "Decathlon"], ["go sport", "GoSport"], ["intersport", "Intersport"],
  ["cultura", "Cultura"], ["action", "Action"], ["gifi", "Gifi"],
  ["maisons du monde", "Maisons-du-Monde"],
  // Auto
  ["norauto", "Norauto"], ["speedy", "Speedy"], ["midas", "Midas"],
  ["euromaster", "Euromaster"], ["feu vert", "Feu-Vert"],
  ["peugeot", "Peugeot"], ["renault", "Renault"], ["citroen", "Citroen"],
  ["volkswagen", "Volkswagen"], ["toyota", "Toyota"], ["dacia", "Dacia"],
  // Tech / Hebergement
  ["ovh", "OVH"], ["o2switch", "O2switch"], ["ionos", "Ionos"],
  ["gandi", "Gandi"], ["scaleway", "Scaleway"], ["infomaniak", "Infomaniak"],
  ["google", "Google"], ["microsoft", "Microsoft"], ["apple", "Apple"],
  ["adobe", "Adobe"], ["spotify", "Spotify"], ["netflix", "Netflix"],
  ["disney", "Disney"], ["canal plus", "Canal-Plus"],
  ["paypal", "PayPal"], ["stripe", "Stripe"],
  // Services / Livraison
  ["la poste", "La-Poste"], ["chronopost", "Chronopost"], ["colissimo", "Colissimo"],
  ["ups", "UPS"], ["fedex", "FedEx"], ["dhl", "DHL"], ["mondial relay", "Mondial-Relay"],
  // BTP / Artisans
  ["plombier", "Plombier"], ["electricien", "Electricien"],
  ["maconnerie", "Maconnerie"], ["peintre", "Peintre"],
  ["chauffagiste", "Chauffagiste"], ["couvreur", "Couvreur"],
  ["menuisier", "Menuisier"], ["serrurier", "Serrurier"],
  ["carreleur", "Carreleur"], ["plaquiste", "Plaquiste"],
  ["jardinier", "Jardinier"], ["paysagiste", "Paysagiste"],
  ["ramoneur", "Ramoneur"], ["architecte", "Architecte"],
  ["geometre", "Geometre"], ["diagnostiqueur", "Diagnostiqueur"],
  // Divers
  ["doctolib", "Doctolib"], ["booking", "Booking"], ["airbnb", "Airbnb"],
  ["uber", "Uber"], ["blablacar", "Blablacar"],
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

function normalize(text) {
  return removeAccents(text).toLowerCase();
}

function generateFilename(text) {
  var norm = normalize(text);
  var date = extractDate(text, norm);
  var docType = detectType(norm);
  var emitter = detectEmitter(norm);
  var detail = extractDetail(norm, docType);
  var name = date + "_" + docType + "_" + emitter;
  if (detail) { name = name + "_" + detail; }
  name = name + ".pdf";
  name = removeAccents(name);
  name = name.replace(/ /g, "-");
  name = name.replace(/[^a-zA-Z0-9_\-\.EUR]/g, "");
  name = name.replace(/-+/g, "-");
  name = name.replace(/_-/g, "_");
  name = name.replace(/-_/g, "_");
  if (name.length > 80) { name = name.substring(0, 76) + ".pdf"; }
  return name;
}

function extractDate(originalText, norm) {
  var match = originalText.match(/(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})/);
  if (match) {
    var d = parseInt(match[1]), m = parseInt(match[2]);
    if (m > 12 && d <= 12) { var tmp = d; d = m; m = tmp; }
    if (m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      return match[3] + "-" + pad(m) + "-" + pad(d);
    }
  }
  match = originalText.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (match) { return match[0]; }
  var moisMap = {
    "janvier": "01", "fevrier": "02", "mars": "03", "avril": "04",
    "mai": "05", "juin": "06", "juillet": "07", "aout": "08",
    "septembre": "09", "octobre": "10", "novembre": "11", "decembre": "12"
  };
  for (var m2 in moisMap) {
    var regex = new RegExp("(\\d{1,2})\\s+" + m2 + "\\s+(\\d{4})");
    match = norm.match(regex);
    if (match) {
      return match[2] + "-" + moisMap[m2] + "-" + pad(parseInt(match[1]));
    }
  }
  for (var m3 in moisMap) {
    var regex2 = new RegExp(m3 + "\\s+(\\d{4})");
    match = norm.match(regex2);
    if (match) {
      return match[1] + "-" + moisMap[m3] + "-01";
    }
  }
  return "0000-00-00";
}

function pad(n) {
  return n < 10 ? "0" + n : "" + n;
}

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

function detectEmitter(norm) {
  var lines = norm.split("\n");
  var header = "";
  for (var h = 0; h < Math.min(lines.length, 10); h++) {
    header += lines[h] + " ";
  }
  for (var e = 0; e < KNOWN_EMITTERS.length; e++) {
    if (header.indexOf(KNOWN_EMITTERS[e][0]) > -1) {
      return KNOWN_EMITTERS[e][1];
    }
  }
  for (var f = 0; f < KNOWN_EMITTERS.length; f++) {
    if (norm.indexOf(KNOWN_EMITTERS[f][0]) > -1) {
      return KNOWN_EMITTERS[f][1];
    }
  }
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

function extractDetail(norm, docType) {
  if (docType === "Facture" || docType === "Devis" || docType === "Quittance") {
    var montant = extractMontant(norm);
    if (montant) return montant;
  }
  if (docType === "Avis") {
    if (norm.indexOf("taxe fonciere") > -1) return "Taxe-Fonciere";
    if (norm.indexOf("taxe d habitation") > -1) return "Taxe-Habitation";
    if (norm.indexOf("impot sur le revenu") > -1) return "Impot-Revenu";
    if (norm.indexOf("cotisation fonciere") > -1) return "CFE";
    if (norm.indexOf("ifi") > -1) return "IFI";
    if (norm.indexOf("contribution sociale") > -1) return "Contrib-Sociale";
  }
  if (docType === "Bulletin" || docType === "Releve") {
    var moisNoms = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
      "juillet", "aout", "septembre", "octobre", "novembre", "decembre"];
    for (var j = 0; j < moisNoms.length; j++) {
      if (norm.indexOf(moisNoms[j]) > -1) {
        var regAnnee = new RegExp(moisNoms[j] + "\\s*(\\d{4})");
        var matchA = norm.match(regAnnee);
        if (matchA) {
          return moisNoms[j].charAt(0).toUpperCase() + moisNoms[j].slice(1) + matchA[1];
        }
        return moisNoms[j].charAt(0).toUpperCase() + moisNoms[j].slice(1);
      }
    }
  }
  if (docType === "Contrat") {
    if (norm.indexOf("bail") > -1) return "Bail";
    if (norm.indexOf("travaux") > -1) return "Travaux";
    if (norm.indexOf("assurance") > -1) return "Assurance";
    if (norm.indexOf("maintenance") > -1) return "Maintenance";
    if (norm.indexOf("location") > -1) return "Location";
    if (norm.indexOf("prestation") > -1) return "Prestation";
    if (norm.indexOf("abonnement") > -1) return "Abonnement";
  }
  if (docType === "Attestation") {
    if (norm.indexOf("domicile") > -1) return "Domicile";
    if (norm.indexOf("assurance") > -1) return "Assurance";
    if (norm.indexOf("responsabilite civile") > -1) return "RC";
    if (norm.indexOf("travail") > -1) return "Travail";
    if (norm.indexOf("hebergement") > -1) return "Hebergement";
    if (norm.indexOf("droits") > -1) return "Droits";
    if (norm.indexOf("formation") > -1) return "Formation";
    if (norm.indexOf("scolarite") > -1) return "Scolarite";
    if (norm.indexOf("vigilance") > -1) return "Vigilance";
  }
  if (docType === "Courrier") {
    if (norm.indexOf("resiliation") > -1) return "Resiliation";
    if (norm.indexOf("reclamation") > -1) return "Reclamation";
    if (norm.indexOf("mise en demeure") > -1) return "Mise-en-demeure";
    if (norm.indexOf("preavis") > -1) return "Preavis";
    if (norm.indexOf("convocation") > -1) return "Convocation";
    if (norm.indexOf("rappel") > -1) return "Rappel";
    if (norm.indexOf("renouvellement") > -1) return "Renouvellement";
    if (norm.indexOf("confirmation") > -1) return "Confirmation";
    if (norm.indexOf("refus") > -1) return "Refus";
    if (norm.indexOf("acceptation") > -1) return "Acceptation";
  }
  if (docType === "Acte") {
    if (norm.indexOf("vente") > -1) return "Vente";
    if (norm.indexOf("donation") > -1) return "Donation";
    if (norm.indexOf("succession") > -1) return "Succession";
    if (norm.indexOf("naissance") > -1) return "Naissance";
    if (norm.indexOf("mariage") > -1) return "Mariage";
    if (norm.indexOf("deces") > -1) return "Deces";
  }
  if (docType === "Rapport") {
    if (norm.indexOf("expertise") > -1) return "Expertise";
    if (norm.indexOf("audit") > -1) return "Audit";
    if (norm.indexOf("diagnostic") > -1) return "Diagnostic";
    if (norm.indexOf("annuel") > -1) return "Annuel";
    if (norm.indexOf("activite") > -1) return "Activite";
    if (norm.indexOf("incident") > -1) return "Incident";
  }
  return "";
}

function extractMontant(norm) {
  var patterns = [
    /(?:total\s*ttc|net\s*a\s*payer|montant\s*ttc|montant\s*total|montant\s*du|total\s*general)[:\s]*(\d[\d\s]*[,\.]\d{2})/,
    /(\d[\d\s]*[,\.]\d{2})\s*(?:€|eur|euros)/,
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
