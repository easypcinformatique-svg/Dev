"""Préparation mensuelle des pièces pour le comptable (dépôt sur Cegid).

Le 1er du mois, l'agent prépare dans Drive le dossier
« Pizza Napoli/Comptable/AAAA-MM à déposer sur Cegid » : une copie de chaque
facture du mois écoulé, un récapitulatif CSV des factures et un CSV des ventes
jour par jour. Un gérant glisse le dossier sur Cegid : l'agent ne dépose rien.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date

from . import config
from .factures import COL, factures_du_mois
from .outils import lire_date, lire_nombre

_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


def mois_precedent(aujourdhui: date) -> tuple[int, int]:
    return (aujourdhui.year - 1, 12) if aujourdhui.month == 1 else (aujourdhui.year, aujourdhui.month - 1)


def nom_dossier(annee: int, mois: int) -> str:
    return f"{annee}-{mois:02d} à déposer sur Cegid"


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


def preparer_depot(g, lignes_factures: list[list[str]], lignes_ventes: list[list[str]],
                   aujourdhui: date) -> str:
    """Prépare le dossier du mois écoulé. Renvoie une phrase pour le rapport."""
    annee, mois = mois_precedent(aujourdhui)
    nom_mois = f"{_MOIS[mois - 1]} {annee}"
    dossier = g.dossier("Comptable", nom_dossier(annee, mois))
    du_mois = factures_du_mois(lignes_factures, annee, mois)
    ventes = [l for l in lignes_ventes if l and (d := lire_date(l[0])) and (d.year, d.month) == (annee, mois)]

    g.deposer(dossier, f"factures_{annee}-{mois:02d}.csv", _csv(config.ONGLETS["Factures"], du_mois), "text/csv")
    g.deposer(dossier, f"ventes_{annee}-{mois:02d}.csv", _csv(config.ONGLETS["Ventes"], ventes), "text/csv")

    copiees, absentes = 0, []
    for l in du_mois:
        id_ = id_drive(l[COL["Fichier"]])
        if not id_:
            absentes.append(l[COL["Fournisseur"]] or "?")
            continue
        g.copier(id_, dossier)
        copiees += 1

    total = f"{_total(du_mois, 'TTC'):.2f}".replace(".", ",")
    phrase = (f"Dossier Cegid de {nom_mois} prêt dans Drive (Pizza Napoli/Comptable/{nom_dossier(annee, mois)}) : "
              f"{copiees} facture(s), total TTC {total} €, et les ventes du mois. Glissez-le sur Cegid.")
    if absentes:
        phrase += f" Fichier introuvable pour : {', '.join(absentes)}."
    return phrase
