"""Envoi mensuel au comptable : préparé le 1er du mois, envoyé par un gérant.

L'agent crée un BROUILLON dans Gmail avec les factures du mois écoulé en pièces
jointes, un récapitulatif CSV des factures et un CSV des ventes jour par jour.
Un gérant relit et clique sur « Envoyer » : c'est la validation.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from . import config
from .factures import COL, factures_du_mois
from .outils import lire_date, lire_nombre

LIMITE_PIECES = 18 * 1024 * 1024   # Gmail refuse au-delà de 25 Mo encodés
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def mois_precedent(aujourdhui: date) -> tuple[int, int]:
    return (aujourdhui.year - 1, 12) if aujourdhui.month == 1 else (aujourdhui.year, aujourdhui.month - 1)


def _csv(entetes: list[str], lignes: list[list]) -> bytes:
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(entetes)
    w.writerows(lignes)
    return f.getvalue().encode("utf-8-sig")   # BOM : Excel ouvre les accents correctement


def id_drive(lien: str) -> str | None:
    m = re.search(r"/d/([\w-]+)", lien) or re.search(r"[?&]id=([\w-]+)", lien)
    return m.group(1) if m else None


def _total(lignes, colonne) -> float:
    return sum(lire_nombre(l[COL[colonne]]) or 0.0 for l in lignes)


def preparer(g, lignes_factures: list[list[str]], lignes_ventes: list[list[str]], aujourdhui: date) -> str:
    """Crée le brouillon. Renvoie une phrase pour le rapport."""
    if not config.COMPTABLE:
        return "Adresse du comptable non renseignée (COMPTABLE_EMAIL) : brouillon non préparé."
    annee, mois = mois_precedent(aujourdhui)
    nom_mois = f"{_MOIS[mois - 1]} {annee}"
    du_mois = factures_du_mois(lignes_factures, annee, mois)
    ventes = [l for l in lignes_ventes if l and (d := lire_date(l[0])) and (d.year, d.month) == (annee, mois)]

    pieces = [
        (f"factures_{annee}-{mois:02d}.csv", "text/csv", _csv(config.ONGLETS["Factures"], du_mois)),
        (f"ventes_{annee}-{mois:02d}.csv", "text/csv", _csv(config.ONGLETS["Ventes"], ventes)),
    ]
    taille, non_jointes = 0, []
    for l in du_mois:
        lien = l[COL["Fichier"]]
        id_ = id_drive(lien)
        if not id_:
            non_jointes.append(l)
            continue
        donnees = g.telecharger(id_)
        if taille + len(donnees) > LIMITE_PIECES:
            non_jointes.append(l)
            continue
        taille += len(donnees)
        ext = "pdf" if donnees[:4] == b"%PDF" else "jpg"
        mime = "application/pdf" if ext == "pdf" else "image/jpeg"
        pieces.append((f"{l[COL['Date facture']] or l[COL['Reçue le']]}_{l[COL['Fournisseur']]}.{ext}", mime, donnees))

    texte = (
        f"Bonjour,\n\nVeuillez trouver ci-joint les pièces de Pizza Napoli pour {nom_mois} :\n"
        f"- {len(du_mois)} facture(s) fournisseurs, total TTC {_total(du_mois, 'TTC'):.2f} € "
        f"(récapitulatif dans factures_{annee}-{mois:02d}.csv) ;\n"
        f"- les ventes jour par jour issues des Z de caisse (ventes_{annee}-{mois:02d}.csv).\n"
    )
    if non_jointes:
        texte += "\nFactures trop volumineuses pour être jointes, accessibles ici :\n" + "".join(
            f"- {l[COL['Fournisseur']]} {l[COL['Date facture']]} : {l[COL['Fichier']]}\n" for l in non_jointes)
    texte += "\nBien cordialement,\nPizza Napoli Carpentras"

    g.brouillon([config.COMPTABLE], f"Pizza Napoli — pièces comptables de {nom_mois}", texte, pieces=pieces)
    return (f"Brouillon pour le comptable prêt dans Gmail : {len(du_mois)} facture(s) de {nom_mois}. "
            "Relisez-le puis cliquez sur « Envoyer ».")
