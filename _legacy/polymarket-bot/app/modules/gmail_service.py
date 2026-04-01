"""Module de récupération des factures depuis Gmail.

Utilise l'API Gmail pour :
- Rechercher les emails contenant des factures en PJ
- Télécharger les pièces jointes (PDF, images)
- Éviter les doublons via le message_id
"""

import base64
import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class GmailService:
    """Service de récupération de factures depuis Gmail."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    def __init__(self, credentials: Credentials, upload_folder: str):
        self.service = build("gmail", "v1", credentials=credentials)
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def rechercher_factures(self, query: str = None, max_results: int = 50):
        """Recherche les emails contenant des factures en PJ.

        Args:
            query: Requête Gmail (ex: "has:attachment filename:pdf subject:facture")
            max_results: Nombre max de résultats

        Returns:
            Liste de messages Gmail
        """
        if query is None:
            query = (
                "has:attachment "
                "(filename:pdf OR filename:jpg OR filename:png) "
                "subject:(facture OR invoice OR reçu OR avoir)"
            )

        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        return results.get("messages", [])

    def recuperer_pieces_jointes(self, message_id: str):
        """Récupère les PJ d'un email et les sauvegarde.

        Args:
            message_id: ID du message Gmail

        Returns:
            Liste de dicts avec les infos des fichiers sauvegardés
        """
        message = (
            self.service.users()
            .messages()
            .get(userId="me", id=message_id)
            .execute()
        )

        fichiers = []
        parts = message.get("payload", {}).get("parts", [])

        # Extraire la date de l'email
        headers = message.get("payload", {}).get("headers", [])
        date_email = None
        expediteur = None
        sujet = None
        for header in headers:
            if header["name"].lower() == "date":
                date_email = header["value"]
            elif header["name"].lower() == "from":
                expediteur = header["value"]
            elif header["name"].lower() == "subject":
                sujet = header["value"]

        for part in parts:
            filename = part.get("filename", "")
            if not filename:
                continue

            # Vérifier que c'est un type de fichier utile
            ext = os.path.splitext(filename)[1].lower()
            if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".tiff"):
                continue

            attachment_id = part.get("body", {}).get("attachmentId")
            if not attachment_id:
                continue

            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            data = base64.urlsafe_b64decode(attachment["data"])

            # Créer un sous-dossier par mois
            now = datetime.now(timezone.utc)
            month_folder = os.path.join(
                self.upload_folder, "gmail", now.strftime("%Y-%m")
            )
            os.makedirs(month_folder, exist_ok=True)

            # Nom de fichier unique pour éviter les collisions
            safe_filename = f"{message_id[:8]}_{filename}"
            filepath = os.path.join(month_folder, safe_filename)

            with open(filepath, "wb") as f:
                f.write(data)

            fichiers.append(
                {
                    "filename": filename,
                    "filepath": filepath,
                    "message_id": message_id,
                    "date_email": date_email,
                    "expediteur": expediteur,
                    "sujet": sujet,
                    "taille": len(data),
                }
            )

        return fichiers

    def synchroniser(self, db_session, Facture, SyncLog, query: str = None):
        """Synchronise les factures Gmail avec la base de données.

        Args:
            db_session: Session SQLAlchemy
            Facture: Modèle Facture
            SyncLog: Modèle SyncLog
            query: Requête Gmail optionnelle

        Returns:
            SyncLog avec le résultat de la synchronisation
        """
        log = SyncLog(source="gmail", statut="en_cours")
        db_session.add(log)
        db_session.commit()

        try:
            messages = self.rechercher_factures(query)
            nb_importees = 0

            for msg in messages:
                msg_id = msg["id"]

                # Vérifier si déjà importé
                existant = Facture.query.filter_by(gmail_message_id=msg_id).first()
                if existant:
                    continue

                fichiers = self.recuperer_pieces_jointes(msg_id)

                for f in fichiers:
                    facture = Facture(
                        fournisseur_nom=f.get("expediteur", "Inconnu"),
                        source="gmail",
                        fichier_path=f["filepath"],
                        fichier_nom=f["filename"],
                        gmail_message_id=msg_id,
                        statut="a_verifier",
                    )
                    db_session.add(facture)
                    nb_importees += 1

            db_session.commit()

            log.statut = "succes"
            log.factures_importees = nb_importees
            log.finished_at = datetime.now(timezone.utc)
            log.message = f"{nb_importees} facture(s) importée(s) depuis Gmail"
            db_session.commit()

        except Exception as e:
            log.statut = "erreur"
            log.message = str(e)
            log.finished_at = datetime.now(timezone.utc)
            db_session.commit()

        return log
