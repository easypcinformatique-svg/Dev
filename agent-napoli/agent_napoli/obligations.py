"""Obligations légales : TVA, URSSAF, assurances, HACCP, contrats.

Les gérants les saisissent dans l'onglet « Obligations » du tableur
(Libellé, Échéance AAAA-MM-JJ, Récurrence, Notes). L'agent place chaque
prochaine échéance dans Google Agenda avec rappels à J-7 et J-1, et la
signale dans le rapport de 9h.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from . import config
from .outils import lire_date

COL = {nom: i for i, nom in enumerate(config.ONGLETS["Obligations"])}
_PAS_EN_MOIS = {"mensuelle": 1, "trimestrielle": 3, "semestrielle": 6, "annuelle": 12}


def _ajouter_mois(d: date, mois: int) -> date:
    m = d.month - 1 + mois
    annee, m = d.year + m // 12, m % 12 + 1
    return date(annee, m, min(d.day, calendar.monthrange(annee, m)[1]))


def prochaine(echeance: date, recurrence: str, aujourdhui: date) -> date | None:
    """Prochaine occurrence à partir d'aujourd'hui (incluse). None si échéance unique passée."""
    pas = _PAS_EN_MOIS.get(recurrence.strip().lower())
    if pas is None:
        return echeance if echeance >= aujourdhui else None
    n = 0
    d = echeance
    while d < aujourdhui:
        n += pas
        d = _ajouter_mois(echeance, n)   # depuis la date d'origine : un 31 reste un 31 quand il existe
    return d


@dataclass
class Obligation:
    ligne: int
    libelle: str
    jour: date
    notes: str
    lien_agenda: str

    def jours_restants(self, aujourdhui: date) -> int:
        return (self.jour - aujourdhui).days


def lire(lignes: list[list[str]], aujourdhui: date) -> tuple[list[Obligation], list[str]]:
    """Renvoie les prochaines occurrences, et les lignes mal remplies."""
    res, erreurs = [], []
    for i, l in enumerate(lignes):
        l = l + [""] * (len(COL) - len(l))
        libelle = l[COL["Libellé"]].strip()
        if not libelle:
            continue
        d = lire_date(l[COL["Échéance"]])
        if d is None:
            erreurs.append(f"« {libelle} » : échéance illisible ({l[COL['Échéance']]!r}, format attendu JJ/MM/AAAA)")
            continue
        p = prochaine(d, l[COL["Récurrence"]] or "unique", aujourdhui)
        if p:
            res.append(Obligation(i, libelle, p, l[COL["Notes"]], l[COL["Agenda"]]))
    return sorted(res, key=lambda o: o.jour), erreurs


def synchroniser_agenda(g, obligations: list[Obligation]) -> int:
    """Crée les évènements manquants. Renvoie le nombre d'obligations traitées."""
    for o in obligations:
        cle = f"{o.libelle}|{o.jour.isoformat()}"
        lien = g.evenement(cle, f"Échéance : {o.libelle}", o.jour.isoformat(),
                           o.notes or "Échéance suivie par l'agent Pizza Napoli.", config.RAPPEL_JOURS)
        if lien and lien != o.lien_agenda:
            g.ecrire_cellule("Obligations", o.ligne, COL["Agenda"], lien)
    return len(obligations)
