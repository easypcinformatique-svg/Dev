"""Module de synchronisation des scans depuis Google Drive.

Surveille un dossier Google Drive contenant les factures scannées
et les télécharge automatiquement.
"""

import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class DriveService:
    """Service de synchronisation avec Google Drive."""

    SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

    # Types MIME supportés pour les factures
    MIME_TYPES_FACTURE = [
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    ]

    def __init__(self, credentials: Credentials, upload_folder: str):
        self.service = build("drive", "v3", credentials=credentials)
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def lister_fichiers(self, folder_id: str, max_results: int = 100):
        """Liste les fichiers dans un dossier Drive.

        Args:
            folder_id: ID du dossier Google Drive
            max_results: Nombre max de résultats

        Returns:
            Liste de fichiers Drive
        """
        mime_filter = " or ".join(
            f"mimeType='{m}'" for m in self.MIME_TYPES_FACTURE
        )
        query = f"'{folder_id}' in parents and ({mime_filter}) and trashed=false"

        results = (
            self.service.files()
            .list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, mimeType, createdTime, modifiedTime, size)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        return results.get("files", [])

    def telecharger_fichier(self, file_id: str, filename: str):
        """Télécharge un fichier depuis Drive.

        Args:
            file_id: ID du fichier Drive
            filename: Nom du fichier

        Returns:
            Chemin du fichier sauvegardé
        """
        now = datetime.now(timezone.utc)
        month_folder = os.path.join(
            self.upload_folder, "drive_scans", now.strftime("%Y-%m")
        )
        os.makedirs(month_folder, exist_ok=True)

        safe_filename = f"{file_id[:8]}_{filename}"
        filepath = os.path.join(month_folder, safe_filename)

        request = self.service.files().get_media(fileId=file_id)
        with open(filepath, "wb") as f:
            f.write(request.execute())

        return filepath

    def synchroniser(self, db_session, Facture, SyncLog, folder_id: str):
        """Synchronise les scans Drive avec la base de données.

        Args:
            db_session: Session SQLAlchemy
            Facture: Modèle Facture
            SyncLog: Modèle SyncLog
            folder_id: ID du dossier Google Drive

        Returns:
            SyncLog avec le résultat de la synchronisation
        """
        log = SyncLog(source="drive", statut="en_cours")
        db_session.add(log)
        db_session.commit()

        try:
            fichiers = self.lister_fichiers(folder_id)
            nb_importees = 0

            for f in fichiers:
                file_id = f["id"]

                # Vérifier si déjà importé
                existant = Facture.query.filter_by(drive_file_id=file_id).first()
                if existant:
                    continue

                filepath = self.telecharger_fichier(file_id, f["name"])

                facture = Facture(
                    fournisseur_nom="Scan - à identifier",
                    source="drive_scan",
                    fichier_path=filepath,
                    fichier_nom=f["name"],
                    drive_file_id=file_id,
                    statut="a_verifier",
                )
                db_session.add(facture)
                nb_importees += 1

            db_session.commit()

            log.statut = "succes"
            log.factures_importees = nb_importees
            log.finished_at = datetime.now(timezone.utc)
            log.message = f"{nb_importees} scan(s) importé(s) depuis Drive"
            db_session.commit()

        except Exception as e:
            log.statut = "erreur"
            log.message = str(e)
            log.finished_at = datetime.now(timezone.utc)
            db_session.commit()

        return log
