"""Accès à Gmail, Drive, Sheets et Agenda du compte de la pizzeria.

L'authentification utilise un jeton de rafraîchissement OAuth obtenu une seule
fois avec autoriser_google.py. En mode essai (essai=True), aucune écriture n'est
faite : chaque action est seulement journalisée.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

from . import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.events",
]
_DOSSIER = "application/vnd.google-apps.folder"
_TABLEUR = "application/vnd.google-apps.spreadsheet"


@dataclass
class PieceJointe:
    nom: str
    type_mime: str
    id_piece: str | None = None
    donnees: bytes | None = None


@dataclass
class Message:
    id: str
    fil: str
    expediteur: str
    destinataire: str
    objet: str
    date: str
    id_message: str               # en-tête Message-ID, pour répondre dans le fil
    html: str = ""
    texte: str = ""
    pieces: list[PieceJointe] = field(default_factory=list)


def _identifiants() -> Credentials:
    manquants = [v for v in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")
                 if not os.getenv(v)]
    if manquants:
        raise RuntimeError("Variables manquantes : " + ", ".join(manquants))
    return Credentials(
        None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def _b64(texte: str) -> bytes:
    return base64.urlsafe_b64decode(texte + "=" * (-len(texte) % 4))


class Google:
    def __init__(self, essai: bool = False, journal=print):
        creds = _identifiants()
        self.essai = essai
        self.journal = journal
        self.gmail = build("gmail", "v1", credentials=creds, cache_discovery=False)
        self.drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.agenda = build("calendar", "v3", credentials=creds, cache_discovery=False)
        self._libelles: dict[str, str] | None = None
        self._dossiers: dict[tuple, str] = {}
        self._classeur: str | None = None

    # ------------------------------------------------------------------ Gmail
    def chercher(self, requete: str, maximum: int = 200) -> list[str]:
        ids, page = [], None
        while len(ids) < maximum:
            r = self.gmail.users().messages().list(
                userId="me", q=requete, pageToken=page, maxResults=min(100, maximum)).execute()
            ids += [m["id"] for m in r.get("messages", [])]
            page = r.get("nextPageToken")
            if not page:
                break
        return ids[:maximum]

    def etiquettes(self, id_: str) -> set[str]:
        m = self.gmail.users().messages().get(userId="me", id=id_, format="minimal").execute()
        return set(m.get("labelIds", []))

    def lire(self, id_: str) -> Message:
        m = self.gmail.users().messages().get(userId="me", id=id_, format="full").execute()
        entetes = {h["name"].lower(): h["value"] for h in m["payload"].get("headers", [])}
        msg = Message(id=m["id"], fil=m["threadId"], expediteur=entetes.get("from", ""),
                      destinataire=entetes.get("to", ""), objet=entetes.get("subject", ""),
                      date=entetes.get("date", ""), id_message=entetes.get("message-id", ""))

        def parcourir(partie):
            mime = partie.get("mimeType", "")
            corps = partie.get("body", {})
            if partie.get("filename"):
                msg.pieces.append(PieceJointe(partie["filename"], mime, corps.get("attachmentId"),
                                              _b64(corps["data"]) if corps.get("data") else None))
            elif mime == "text/html" and corps.get("data"):
                msg.html += _b64(corps["data"]).decode("utf-8", "replace")
            elif mime == "text/plain" and corps.get("data"):
                msg.texte += _b64(corps["data"]).decode("utf-8", "replace")
            for sous in partie.get("parts", []):
                parcourir(sous)

        parcourir(m["payload"])
        return msg

    def piece(self, msg: Message, piece: PieceJointe) -> bytes:
        if piece.donnees is None:
            r = self.gmail.users().messages().attachments().get(
                userId="me", messageId=msg.id, id=piece.id_piece).execute()
            piece.donnees = _b64(r["data"])
        return piece.donnees

    def libelle(self, nom: str) -> str:
        if self._libelles is None:
            r = self.gmail.users().labels().list(userId="me").execute()
            self._libelles = {l["name"]: l["id"] for l in r.get("labels", [])}
        if nom not in self._libelles:
            if self.essai:
                return f"essai-{nom}"
            r = self.gmail.users().labels().create(userId="me", body={"name": nom}).execute()
            self._libelles[nom] = r["id"]
        return self._libelles[nom]

    def libelles_utilisateur(self) -> list[str]:
        """Libellés créés par les gérants (hors libellés système et hors « Agent/ »)."""
        r = self.gmail.users().labels().list(userId="me").execute()
        return sorted(l["name"] for l in r.get("labels", [])
                      if l.get("type") == "user" and not l["name"].startswith("Agent/"))

    def etiqueter(self, msg: Message, noms: list[str]) -> None:
        if self.essai:
            self.journal("gmail", "étiquettes (essai)", f"{msg.objet[:60]} -> {', '.join(noms)}")
            return
        self.gmail.users().messages().modify(
            userId="me", id=msg.id, body={"addLabelIds": [self.libelle(n) for n in noms]}).execute()

    def _mail(self, a: list[str], objet: str, html: str, texte: str = "",
              pieces: list[tuple[str, str, bytes]] = (), en_reponse_a: Message | None = None) -> dict:
        e = EmailMessage()
        e["From"] = f"Agent Pizza Napoli <{config.BOITE_PIZZERIA}>"
        e["To"] = ", ".join(a)
        e["Subject"] = objet
        if en_reponse_a and en_reponse_a.id_message:
            e["In-Reply-To"] = en_reponse_a.id_message
            e["References"] = en_reponse_a.id_message
        e.set_content(texte or "Ce message est au format HTML.")
        if html:
            e.add_alternative(html, subtype="html")
        for nom, mime, donnees in pieces:
            principal, _, sous = mime.partition("/")
            e.add_attachment(donnees, maintype=principal, subtype=sous or "octet-stream", filename=nom)
        corps = {"raw": base64.urlsafe_b64encode(e.as_bytes()).decode()}
        if en_reponse_a:
            corps["threadId"] = en_reponse_a.fil
        return corps

    def envoyer(self, a: list[str], objet: str, html: str) -> None:
        """Envoie le rapport. En essai aussi (seule écriture de l'essai), marqué [ESSAI]."""
        if self.essai:
            objet = f"[ESSAI] {objet}"
        self.gmail.users().messages().send(userId="me", body=self._mail(a, objet, html)).execute()

    def brouillon(self, a: list[str], objet: str, texte: str, html: str = "",
                  pieces: list[tuple[str, str, bytes]] = (), en_reponse_a: Message | None = None) -> None:
        if self.essai:
            self.journal("gmail", "brouillon (essai)", f"{objet} -> {', '.join(a)}")
            return
        message = self._mail(a, objet, html, texte, pieces, en_reponse_a)
        self.gmail.users().drafts().create(userId="me", body={"message": message}).execute()

    def nb_brouillons(self) -> int:
        r = self.gmail.users().drafts().list(userId="me", maxResults=100).execute()
        return len(r.get("drafts", []))

    # ------------------------------------------------------------------ Drive
    def _trouver(self, nom: str, parent: str | None, mime: str | None = None) -> str | None:
        q = [f"name = '{nom.replace(chr(39), chr(92) + chr(39))}'", "trashed = false"]
        if parent:
            q.append(f"'{parent}' in parents")
        if mime:
            q.append(f"mimeType = '{mime}'")
        r = self.drive.files().list(q=" and ".join(q), fields="files(id)", pageSize=1).execute()
        f = r.get("files", [])
        return f[0]["id"] if f else None

    def dossier(self, *chemin: str) -> str:
        """Identifiant du dossier « Pizza Napoli/<chemin> », créé au besoin."""
        cle = (config.DOSSIER_RACINE, *chemin)
        if cle in self._dossiers:
            return self._dossiers[cle]
        parent = None
        for i, nom in enumerate(cle):
            sous_cle = cle[: i + 1]
            if sous_cle in self._dossiers:
                parent = self._dossiers[sous_cle]
                continue
            id_ = self._trouver(nom, parent, _DOSSIER)
            if id_ is None:
                if self.essai:
                    id_ = f"essai-{'/'.join(sous_cle)}"
                else:
                    meta = {"name": nom, "mimeType": _DOSSIER, **({"parents": [parent]} if parent else {})}
                    id_ = self.drive.files().create(body=meta, fields="id").execute()["id"]
                    self.journal("drive", "dossier créé", "/".join(sous_cle))
            self._dossiers[sous_cle] = parent = id_
        return parent

    def deposer(self, dossier: str, nom: str, donnees: bytes, mime: str) -> str:
        """Dépose un fichier, renvoie son lien."""
        if self.essai:
            self.journal("drive", "dépôt (essai)", nom)
            return f"(essai) {nom}"
        f = self.drive.files().create(
            body={"name": nom, "parents": [dossier]},
            media_body=MediaInMemoryUpload(donnees, mimetype=mime),
            fields="id, webViewLink").execute()
        return f["webViewLink"]

    def copier(self, id_: str, dossier: str) -> None:
        if self.essai:
            self.journal("drive", "copie (essai)", id_)
            return
        self.drive.files().copy(fileId=id_, body={"parents": [dossier]}, fields="id").execute()

    def lister(self, dossier: str) -> list[dict]:
        r = self.drive.files().list(
            q=f"'{dossier}' in parents and trashed = false and mimeType != '{_DOSSIER}'",
            fields="files(id, name, mimeType, webViewLink, createdTime)", pageSize=200).execute()
        return r.get("files", [])

    def telecharger(self, id_: str, mime: str = "") -> bytes:
        if mime == "application/vnd.google-apps.spreadsheet":
            return self.drive.files().export(fileId=id_, mimeType="text/csv").execute()
        return self.drive.files().get_media(fileId=id_).execute()

    def deplacer(self, id_: str, vers: str, nouveau_nom: str) -> str:
        if self.essai:
            self.journal("drive", "déplacement (essai)", nouveau_nom)
            return f"(essai) {nouveau_nom}"
        f = self.drive.files().get(fileId=id_, fields="parents").execute()
        f = self.drive.files().update(
            fileId=id_, addParents=vers, removeParents=",".join(f.get("parents", [])),
            body={"name": nouveau_nom}, fields="webViewLink").execute()
        return f["webViewLink"]

    # ----------------------------------------------------------------- Sheets
    def classeur(self) -> str:
        if self._classeur:
            return self._classeur
        racine = self.dossier()
        id_ = config.CLASSEUR_ID or self._trouver(config.CLASSEUR, racine, _TABLEUR)
        if id_ is None and not self.essai:
            id_ = self.drive.files().create(
                body={"name": config.CLASSEUR, "mimeType": _TABLEUR, "parents": [racine]},
                fields="id").execute()["id"]
            self.journal("sheets", "classeur créé", config.CLASSEUR)
        if id_ is None:
            return "essai-classeur"
        existants = {o["properties"]["title"] for o in
                     self.sheets.spreadsheets().get(spreadsheetId=id_).execute()["sheets"]}
        for onglet, entetes in config.ONGLETS.items():
            if onglet in existants or self.essai:
                continue
            self.sheets.spreadsheets().batchUpdate(spreadsheetId=id_, body={
                "requests": [{"addSheet": {"properties": {"title": onglet}}}]}).execute()
            self.sheets.spreadsheets().values().update(
                spreadsheetId=id_, range=f"'{onglet}'!A1", valueInputOption="RAW",
                body={"values": [entetes]}).execute()
        self._classeur = id_
        return id_

    def lien_classeur(self) -> str:
        id_ = self.classeur()
        return "" if id_.startswith("essai-") else f"https://docs.google.com/spreadsheets/d/{id_}"

    def lignes(self, onglet: str) -> list[list[str]]:
        id_ = self.classeur()
        if id_.startswith("essai-"):
            return []
        r = self.sheets.spreadsheets().values().get(spreadsheetId=id_, range=f"'{onglet}'").execute()
        return r.get("values", [])[1:]

    def ajouter(self, onglet: str, lignes: list[list]) -> None:
        if not lignes:
            return
        if self.essai:
            self.journal("sheets", "ajout (essai)", f"{onglet} : {len(lignes)} ligne(s)")
            return
        self.sheets.spreadsheets().values().append(
            spreadsheetId=self.classeur(), range=f"'{onglet}'!A1", valueInputOption="RAW",
            insertDataOption="INSERT_ROWS", body={"values": lignes}).execute()

    def ecrire_cellule(self, onglet: str, ligne: int, colonne: int, valeur: str) -> None:
        """ligne : numéro de ligne de données (0 = première ligne sous l'en-tête)."""
        if self.essai:
            return
        cellule = f"'{onglet}'!{chr(ord('A') + colonne)}{ligne + 2}"
        self.sheets.spreadsheets().values().update(
            spreadsheetId=self.classeur(), range=cellule, valueInputOption="RAW",
            body={"values": [[valeur]]}).execute()

    # ----------------------------------------------------------------- Agenda
    def evenement(self, cle: str, titre: str, jour: str, description: str, rappels_jours) -> str:
        """Crée (une seule fois) un évènement d'une journée avec rappels. Renvoie son lien."""
        r = self.agenda.events().list(
            calendarId="primary", privateExtendedProperty=f"agent_napoli={cle}", maxResults=1).execute()
        if r.get("items"):
            return r["items"][0].get("htmlLink", "")
        if self.essai:
            self.journal("agenda", "évènement (essai)", f"{jour} {titre}")
            return "(essai)"
        ev = self.agenda.events().insert(calendarId="primary", body={
            "summary": titre,
            "description": description,
            "start": {"date": jour},
            "end": {"date": (date.fromisoformat(jour) + timedelta(days=1)).isoformat()},
            "reminders": {"useDefault": False, "overrides": [
                {"method": "email", "minutes": j * 24 * 60} for j in rappels_jours]},
            "extendedProperties": {"private": {"agent_napoli": cle}},
        }).execute()
        return ev.get("htmlLink", "")
