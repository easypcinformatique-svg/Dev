# GED - Scan OCR + Renommage Automatique

Scenario Make.com qui surveille un dossier Google Drive, extrait le texte via OCR (EdenAI), genere un nom de fichier intelligent via Gemini, renomme/deplace le fichier, et log dans Google Sheets.

## Flux

```
Google Drive (trigger) -> Download -> OCR (EdenAI) -> Nommage IA (Gemini) -> Move/Rename -> Log Sheets
```

## Configuration requise

Remplacer les placeholders dans `make-scenario.json` :

| Placeholder | Description |
|---|---|
| `REMPLACER_PAR_ID_CONNEXION_GDRIVE` | ID connexion Google Drive dans Make |
| `REMPLACER_PAR_ID_DOSSIER_SCANS_ENTRANTS` | ID du dossier Google Drive source |
| `REMPLACER_PAR_ID_DOSSIER_SCANS_TRAITES` | ID du dossier Google Drive destination |
| `REMPLACER_PAR_CLE_EDENAI` | Cle API EdenAI (https://www.edenai.run) |
| `REMPLACER_PAR_CLE_GEMINI` | Cle API Google Gemini |
| `REMPLACER_PAR_ID_CONNEXION_GSHEETS` | ID connexion Google Sheets dans Make |
| `REMPLACER_PAR_ID_SPREADSHEET` | ID du Google Spreadsheet pour les logs |

## Structure Google Drive

```
GED Perso/
  Scans entrants/    <- dossier surveille (trigger)
  Scans traites/     <- destination apres renommage
```

## Format de nommage

```
AAAA-MM-JJ_Type_Emetteur_Detail.pdf
```

Types : Facture, Devis, Contrat, Releve, Avis, Courrier, Bulletin, Attestation, Acte, Quittance, Rapport, Autre

## Google Sheets (Log_GED)

Colonnes attendues : Date traitement | Nom original | Nom final | Taille (Ko) | Texte OCR (extrait) | Statut

## Import dans Make.com

1. Creer un nouveau scenario vide
2. Clic droit > Import Blueprint > coller le contenu de `make-scenario.json`
3. Configurer les connexions Google Drive et Sheets
4. Renseigner les cles API
5. Activer le scenario
