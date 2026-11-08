"""Factures fournisseurs : lecture, classement dans Drive, inscription dans le tableur.

Trois arrivées possibles : PDF joint à un mail, photo envoyée par mail (objet
« FACTURE »), ou fichier déposé dans Drive « Pizza Napoli/Factures/À traiter ».
L'agent ne paie jamais : il range, il note l'échéance, il rappelle.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from . import config, ia
from .outils import lire_date

TYPES_ACCEPTES = {"application/pdf", "image/jpeg", "image/png", "image/webp", "image/gif"}
_EXTENSIONS = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png",
               "image/webp": "webp", "image/gif": "gif"}
COL = {nom: i for i, nom in enumerate(config.ONGLETS["Factures"])}


_date = lire_date


def _slug(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", texte).strip("-")[:40] or "Inconnu"


def nom_fichier(info: dict, type_mime: str) -> str:
    jour = info.get("date_facture") or date.today().isoformat()
    ttc = info.get("montant_ttc")
    montant = f"_{ttc:.2f}EUR".replace(".", ",") if isinstance(ttc, (int, float)) else ""
    numero = f"_{_slug(info['numero'])}" if info.get("numero") else ""
    return f"{jour}_{_slug(info.get('fournisseur', ''))}{numero}{montant}.{_EXTENSIONS[type_mime]}"


def cle(fournisseur: str, numero: str | None) -> tuple[str, str] | None:
    if not numero:
        return None
    return (_slug(fournisseur).lower(), _slug(numero).lower())


def cles_existantes(lignes: list[list[str]]) -> set:
    vues = set()
    for l in lignes:
        l = l + [""] * (len(COL) - len(l))
        k = cle(l[COL["Fournisseur"]], l[COL["N° facture"]])
        if k:
            vues.add(k)
    return vues


def mois_de_classement(info: dict) -> str:
    d = _date(info.get("date_facture")) or date.today()
    return f"{d:%Y-%m}"


def ligne_tableur(info: dict, lien: str, source: str, recue: date) -> list:
    statut = "payée" if info.get("deja_payee") else "à payer"
    return [recue.isoformat(), info.get("fournisseur", ""), info.get("numero") or "",
            info.get("date_facture") or "", info.get("date_echeance") or "",
            info.get("montant_ht"), info.get("montant_tva"), info.get("montant_ttc"),
            statut, info.get("categorie", ""), lien, source]


@dataclass
class Resultat:
    statut: str          # "classée", "doublon", "pas une facture", "erreur"
    detail: str
    info: dict | None = None


def traiter_document(g, donnees: bytes, type_mime: str, source: str, vues: set,
                     id_drive: str | None = None) -> Resultat:
    """Lit un document ; s'il s'agit d'une facture nouvelle, la range et l'inscrit.

    id_drive : si le document est déjà dans Drive (dossier « À traiter »), il est
    déplacé au lieu d'être copié.
    """
    try:
        info = ia.lire_facture(donnees, type_mime, f"Source : {source}.")
    except ia.ErreurIA as e:
        return Resultat("erreur", f"lecture impossible ({e})")
    if not info.get("est_une_facture"):
        return Resultat("pas une facture", source, info)

    k = cle(info.get("fournisseur", ""), info.get("numero"))
    if k and k in vues:
        return Resultat("doublon", f"{info.get('fournisseur')} n° {info.get('numero')} déjà enregistrée", info)

    dossier = g.dossier("Factures", mois_de_classement(info))
    nom = nom_fichier(info, type_mime)
    lien = g.deplacer(id_drive, dossier, nom) if id_drive else g.deposer(dossier, nom, donnees, type_mime)
    g.ajouter("Factures", [ligne_tableur(info, lien, source, date.today())])
    if k:
        vues.add(k)
    ttc = info.get("montant_ttc")
    montant = f"{ttc:.2f} €" if isinstance(ttc, (int, float)) else "montant illisible"
    return Resultat("classée", f"{info.get('fournisseur')} : {montant}", info)


def pieces_facture(msg) -> list:
    return [p for p in msg.pieces if p.type_mime in TYPES_ACCEPTES]


def traiter_mail(g, msg, vues: set) -> list[Resultat]:
    resultats = []
    for p in pieces_facture(msg):
        source = f"mail de {msg.expediteur} — {p.nom}"
        resultats.append(traiter_document(g, g.piece(msg, p), p.type_mime, source, vues))
    return resultats


def traiter_dossier_a_traiter(g, vues: set) -> list[Resultat]:
    dossier = g.dossier("Factures", config.DOSSIER_A_TRAITER)
    resultats = []
    for f in g.lister(dossier):
        if f["mimeType"] not in TYPES_ACCEPTES:
            resultats.append(Resultat("erreur", f"{f['name']} : format non pris en charge"))
            continue
        r = traiter_document(g, g.telecharger(f["id"]), f["mimeType"],
                             f"Drive « À traiter » — {f['name']}", vues, id_drive=f["id"])
        resultats.append(r)
    return resultats


@dataclass
class Echeance:
    fournisseur: str
    montant: str
    jour: date
    lien: str

    def jours_restants(self, aujourdhui: date) -> int:
        return (self.jour - aujourdhui).days


def echeances_a_payer(lignes: list[list[str]], aujourdhui: date, horizon: int = 7) -> list[Echeance]:
    """Factures « à payer » échues ou à échéance dans les `horizon` jours."""
    res = []
    for l in lignes:
        l = l + [""] * (len(COL) - len(l))
        if l[COL["Statut"]].strip().lower() != "à payer":
            continue
        d = _date(l[COL["Échéance"]])
        if d and (d - aujourdhui).days <= horizon:
            res.append(Echeance(l[COL["Fournisseur"]], l[COL["TTC"]], d, l[COL["Fichier"]]))
    return sorted(res, key=lambda e: e.jour)


def factures_du_mois(lignes: list[list[str]], annee: int, mois: int) -> list[list[str]]:
    """Factures dont la date (ou, à défaut, la réception) tombe dans le mois donné."""
    res = []
    for l in lignes:
        l = l + [""] * (len(COL) - len(l))
        d = _date(l[COL["Date facture"]]) or _date(l[COL["Reçue le"]])
        if d and (d.year, d.month) == (annee, mois):
            res.append(l)
    return res
