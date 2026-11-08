"""Suivi du chiffre d'affaires sur l'exercice comptable (1er juillet - 30 juin).

Sources :
- les ventes jour par jour des tickets Z (onglet « Ventes »), y compris l'historique
  relu une fois depuis les anciens mails (python -m agent_napoli --historique) ;
- le CA annuel des liasses fiscales (onglet « Exercices »), lu dans Drive
  « Pizza Napoli/Légal/Liasses ».

Le CA de caisse (Z) et le CA de la liasse ne sont pas strictement identiques
(remises, régularisations du comptable). La projection applique donc l'évolution
mesurée sur la caisse au CA de la liasse : on compare toujours caisse avec caisse.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta

from . import config
from .outils import lire_date, lire_nombre

_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]
COL_V = {nom: i for i, nom in enumerate(config.ONGLETS["Ventes"])}
COL_E = {nom: i for i, nom in enumerate(config.ONGLETS["Exercices"])}


# --- Dates d'exercice ----------------------------------------------------------

def debut_exercice(d: date) -> date:
    m = config.EXERCICE_DEBUT_MOIS
    return date(d.year if d.month >= m else d.year - 1, m, 1)


def fin_exercice(d: date) -> date:
    debut = debut_exercice(d)
    return date(debut.year + 1, debut.month, 1) - timedelta(days=1)


def nom_exercice(d: date) -> str:
    debut = debut_exercice(d)
    return f"{debut.year}-{debut.year + 1}"


def un_an_avant(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:            # 29 février
        return d.replace(year=d.year - 1, day=28)


# --- Lecture du tableur ----------------------------------------------------------

@dataclass
class Jour:
    jour: date
    ca_ht: float
    ticket_moyen: float
    livraison: float | None
    emporter: float | None


def lire_ventes(lignes: list[list[str]]) -> dict[date, Jour]:
    res = {}
    for l in lignes:
        l = list(l) + [""] * (len(COL_V) - len(l))
        d = lire_date(l[COL_V["Date"]])
        ca = lire_nombre(l[COL_V["CA HT"]])
        if d and ca is not None:
            res[d] = Jour(d, ca, lire_nombre(l[COL_V["Ticket moyen"]]) or 0.0,
                          lire_nombre(l[COL_V["Livraison"]]), lire_nombre(l[COL_V["A emporter"]]))
    return res


@dataclass
class Exercice:
    nom: str
    debut: date
    fin: date
    ca_ht: float | None
    resultat: float | None
    objectif: float | None
    source: str


def lire_exercices(lignes: list[list[str]]) -> list[Exercice]:
    res = []
    for l in lignes:
        l = list(l) + [""] * (len(COL_E) - len(l))
        debut, fin = lire_date(l[COL_E["Début"]]), lire_date(l[COL_E["Fin"]])
        if debut and fin:
            res.append(Exercice(l[COL_E["Exercice"]] or f"{debut.year}-{fin.year}", debut, fin,
                                lire_nombre(l[COL_E["CA HT"]]), lire_nombre(l[COL_E["Résultat"]]),
                                lire_nombre(l[COL_E["Objectif CA HT"]]), l[COL_E["Source"]]))
    return res


# --- Suivi -----------------------------------------------------------------------

def _somme(ventes: dict[date, Jour], debut: date, fin: date) -> tuple[float, int]:
    jours = [j for d, j in ventes.items() if debut <= d <= fin]
    return sum(j.ca_ht for j in jours), len(jours)


def _couvert(ventes: dict[date, Jour], debut: date, fin: date) -> bool:
    """Vrai si l'historique couvre la période (des ventes dans ses 10 premiers et derniers jours)."""
    return (any(debut <= d <= debut + timedelta(days=10) for d in ventes)
            and any(fin - timedelta(days=10) <= d <= fin for d in ventes))


@dataclass
class Suivi:
    exercice: str
    depuis: date
    jusqu_au: date
    cumul: float
    cumul_n1: float | None            # même période de l'exercice précédent (caisse)
    ca_n1_liasse: float | None        # CA annuel de l'exercice précédent (liasse)
    projection: float | None
    projection_methode: str           # "saisonnière" ou "linéaire"
    objectif: float | None

    @property
    def evolution(self) -> float | None:
        return (self.cumul - self.cumul_n1) / self.cumul_n1 if self.cumul_n1 else None

    @property
    def ecart_objectif(self) -> float | None:
        if self.projection is None or not self.objectif:
            return None
        return self.projection - self.objectif


def suivre(veille: date, ventes: dict[date, Jour], exercices: list[Exercice]) -> Suivi | None:
    debut, fin = debut_exercice(veille), fin_exercice(veille)
    cumul, nb = _somme(ventes, debut, veille)
    if nb == 0:
        return None
    debut_n1, veille_n1, fin_n1 = un_an_avant(debut), un_an_avant(veille), un_an_avant(fin)
    cumul_n1 = None
    if _couvert(ventes, debut_n1, veille_n1):
        cumul_n1 = _somme(ventes, debut_n1, veille_n1)[0] or None

    precedent = next((e for e in exercices if e.fin == debut - timedelta(days=1)), None)
    courant = next((e for e in exercices if e.debut == debut), None)
    ca_n1 = precedent.ca_ht if precedent else None
    if ca_n1 is None and _couvert(ventes, debut_n1, fin_n1):
        ca_n1 = _somme(ventes, debut_n1, fin_n1)[0]       # à défaut de liasse : total de caisse

    if cumul_n1 and ca_n1:
        projection, methode = ca_n1 * cumul / cumul_n1, "saisonnière"
    else:
        ecoules = (veille - debut).days + 1
        projection, methode = cumul * ((fin - debut).days + 1) / ecoules, "linéaire"

    objectif = courant.objectif if courant and courant.objectif else (
        ca_n1 * (1 + config.OBJECTIF_CROISSANCE) if ca_n1 and config.OBJECTIF_CROISSANCE else None)
    return Suivi(nom_exercice(veille), debut, veille, cumul, cumul_n1, ca_n1, projection, methode, objectif)


@dataclass
class BilanMois:
    nom: str
    ca_ht: float
    ca_ht_n1: float | None
    jours: int
    ticket_moyen: float | None
    part_livraison: float | None


def bilan_mois(annee: int, mois: int, ventes: dict[date, Jour]) -> BilanMois | None:
    debut = date(annee, mois, 1)
    fin = date(annee, mois, calendar.monthrange(annee, mois)[1])
    jours = [j for d, j in ventes.items() if debut <= d <= fin]
    if not jours:
        return None
    ca = sum(j.ca_ht for j in jours)
    debut_n1, fin_n1 = un_an_avant(debut), un_an_avant(fin)
    ca_n1 = _somme(ventes, debut_n1, fin_n1)[0] if _couvert(ventes, debut_n1, fin_n1) else None
    tickets = [j.ticket_moyen for j in jours if j.ticket_moyen]
    salles = [(j.livraison, j.emporter) for j in jours if j.livraison is not None and j.emporter is not None]
    total_salles = sum(a + b for a, b in salles)
    return BilanMois(f"{_MOIS[mois - 1]} {annee}", ca, ca_n1, len(jours),
                     sum(tickets) / len(tickets) if tickets else None,
                     sum(a for a, _ in salles) / total_salles if total_salles else None)
