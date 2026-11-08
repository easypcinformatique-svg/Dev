"""Tri quotidien de la boîte carpentraspizzanapoli@gmail.com.

Chaque mail nouveau reçoit une étiquette « Agent/... ». Le Z de L'Addition est
lu, les factures sont classées, et pour les mails qui attendent une réponse
l'agent prépare un brouillon dans le fil : rien n'est envoyé sans un gérant.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from . import config, factures, ia, z_laddition

PREFIXE_RAPPORT = "[Agent Pizza Napoli]"
_SANS_REPONSE = re.compile(r"no-?reply|ne-pas-repondre|nepasrepondre|mailer-daemon|notification", re.I)


@dataclass
class MailImportant:
    expediteur: str
    objet: str
    resume: str
    action: str | None
    brouillon: bool


@dataclass
class BilanTri:
    par_categorie: dict[str, int] = field(default_factory=dict)
    importants: list[MailImportant] = field(default_factory=list)
    factures: list[factures.Resultat] = field(default_factory=list)
    z: list[z_laddition.Z] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)

    def compter(self, categorie: str) -> None:
        self.par_categorie[categorie] = self.par_categorie.get(categorie, 0) + 1


def est_z(msg) -> bool:
    return config.Z_EXPEDITEUR in msg.expediteur.lower() and config.Z_OBJET.lower() in msg.objet.lower()


def est_facture_deposee(msg) -> bool:
    """Photo ou PDF envoyé exprès par un gérant, objet « FACTURE »."""
    return "facture" in msg.objet.lower() and bool(factures.pieces_facture(msg))


def texte_du_mail(msg) -> str:
    if msg.texte.strip():
        return msg.texte
    return BeautifulSoup(msg.html, "html.parser").get_text("\n", strip=True)


def adresse(expediteur: str) -> str:
    m = re.search(r"<([^>]+)>", expediteur)
    return (m.group(1) if m else expediteur).strip()


def trier(g, vues_factures: set, journal) -> BilanTri:
    bilan = BilanTri()
    traite = g.libelle(config.LIBELLE_TRAITE)
    ids = g.chercher(f"newer_than:{config.JOURS_HISTORIQUE}d -in:drafts -in:chats")
    for id_ in ids:
        etiquettes = g.etiquettes(id_)
        if traite in etiquettes:
            continue
        msg = g.lire(id_)
        if ("SENT" in etiquettes and "INBOX" not in etiquettes) or msg.objet.startswith(PREFIXE_RAPPORT):
            g.etiqueter(msg, [config.LIBELLE_TRAITE])
            continue
        try:
            categorie = _traiter(g, msg, bilan, vues_factures)
        except ia.ErreurIA as e:
            bilan.erreurs.append(f"« {msg.objet[:60]} » : {e} (nouvel essai demain)")
            continue
        except ValueError as e:
            bilan.erreurs.append(f"« {msg.objet[:60]} » : {e}")
            categorie = "z_caisse" if est_z(msg) else "autre"
        bilan.compter(categorie)
        g.etiqueter(msg, [config.LIBELLES[categorie], config.LIBELLE_TRAITE])
    journal("tri", "mails triés", ", ".join(f"{k} : {v}" for k, v in sorted(bilan.par_categorie.items())) or "aucun")
    return bilan


def _traiter(g, msg, bilan: BilanTri, vues_factures: set) -> str:
    if est_z(msg):
        bilan.z.append(z_laddition.lire_z(msg.html or msg.texte, msg.objet))
        return "z_caisse"
    if est_facture_deposee(msg):
        bilan.factures += factures.traiter_mail(g, msg, vues_factures)
        return "facture"

    pieces = [p.nom for p in msg.pieces]
    tri = ia.trier_mail(msg.expediteur, msg.objet, texte_du_mail(msg), pieces)
    categorie = tri["categorie"]
    if categorie == "facture" and factures.pieces_facture(msg):
        bilan.factures += factures.traiter_mail(g, msg, vues_factures)

    brouillon = False
    if (tri.get("brouillon_reponse") and categorie in ("client", "fournisseur", "administratif")
            and not _SANS_REPONSE.search(msg.expediteur)):
        objet = msg.objet if msg.objet.lower().startswith("re:") else f"Re: {msg.objet}"
        g.brouillon([adresse(msg.expediteur)], objet, tri["brouillon_reponse"], en_reponse_a=msg)
        brouillon = True
    if tri.get("important") or brouillon:
        bilan.importants.append(MailImportant(msg.expediteur, msg.objet, tri["resume"], tri.get("action"), brouillon))
    return categorie
