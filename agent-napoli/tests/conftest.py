import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent_napoli.google_api import Message, PieceJointe  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
OBJET_Z = "L'Addition - Votre Z quotidien (PIZZA NAPOLI CARPENTRAS | 2026-10-17)"


class FauxGoogle:
    """Remplace Google : garde en mémoire tout ce que l'agent écrit."""

    LIBELLES = ["Bulletins de paie", "Candidatures LIVREURS", "Factures", "HYGIENES",
                "NOUVELLE COMMANDE", "Ticket Z", "Tickets restaurants"]

    def __init__(self, messages=(), etiquettes=None, fichiers_a_traiter=()):
        self.messages = {m.id: m for m in messages}
        self._etiquettes = etiquettes or {}
        self.fichiers_a_traiter = list(fichiers_a_traiter)
        self.contenus_drive = {}
        self.etiquetes = {}
        self.brouillons = []
        self.envois = []
        self.depots = []
        self.deplacements = []
        self.ajouts = {}
        self.cellules = []
        self.evenements = []
        self.copies = []

    def libelle(self, nom):
        return f"id:{nom}"

    def libelles_utilisateur(self):
        return list(self.LIBELLES)

    def copier(self, id_, dossier):
        self.copies.append((id_, dossier))

    def chercher(self, requete, maximum=200):
        return list(self.messages)

    def etiquettes(self, id_):
        posees = {self.libelle(n) for n in self.etiquetes.get(id_, [])}
        return set(self._etiquettes.get(id_, {"INBOX"})) | posees

    def lire(self, id_):
        return self.messages[id_]

    def piece(self, msg, piece):
        return piece.donnees

    def etiqueter(self, msg, noms):
        self.etiquetes.setdefault(msg.id, []).extend(noms)

    def brouillon(self, a, objet, texte, html="", pieces=(), en_reponse_a=None):
        self.brouillons.append({"a": a, "objet": objet, "texte": texte, "pieces": list(pieces),
                                "fil": en_reponse_a.fil if en_reponse_a else None})

    def envoyer(self, a, objet, html):
        self.envois.append((a, objet, html))

    def dossier(self, *chemin):
        return "/".join(chemin)

    def deposer(self, dossier, nom, donnees, mime):
        self.depots.append((dossier, nom))
        return f"https://drive.google.com/file/d/ID-{len(self.depots)}/view"

    def lister(self, dossier):
        return self.fichiers_a_traiter

    def telecharger(self, id_, mime=""):
        return self.contenus_drive.get(id_, b"%PDF-1.4 faux")

    def deplacer(self, id_, vers, nom):
        self.deplacements.append((id_, vers, nom))
        return f"https://drive.google.com/file/d/{id_}/view"

    def ajouter(self, onglet, lignes):
        self.ajouts.setdefault(onglet, []).extend(lignes)

    def lignes(self, onglet):
        return [list(l) for l in self.ajouts.get(onglet, [])]

    def nb_brouillons(self):
        return len(self.brouillons)

    def lien_classeur(self):
        return "https://docs.google.com/spreadsheets/d/CLASSEUR"

    def ecrire_cellule(self, onglet, ligne, colonne, valeur):
        self.cellules.append((onglet, ligne, colonne, valeur))

    def evenement(self, cle, titre, jour, description, rappels):
        self.evenements.append((cle, titre, jour, tuple(rappels)))
        return f"https://calendar/{len(self.evenements)}"


def mail(id_="m1", expediteur="Client <client@example.com>", objet="Bonjour", texte="Bonjour",
         html="", pieces=()):
    return Message(id=id_, fil=f"fil-{id_}", expediteur=expediteur, destinataire="pizzeria",
                   objet=objet, date="", id_message=f"<{id_}@mail>", html=html, texte=texte,
                   pieces=list(pieces))


def piece_pdf(nom="facture.pdf"):
    return PieceJointe(nom, "application/pdf", donnees=b"%PDF-1.4 facture")


@pytest.fixture
def html_z():
    return (FIXTURES / "z_2026-10-17.html").read_text(encoding="utf-8")


@pytest.fixture
def journal():
    lignes = []

    def j(module, action, detail=""):
        lignes.append((module, action, detail))
    j.lignes = lignes
    return j
