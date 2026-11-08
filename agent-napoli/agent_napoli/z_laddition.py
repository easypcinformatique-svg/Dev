"""Lecture du Z quotidien envoyé par L'Addition, et contrôles de caisse.

Le mail « L'Addition - Votre Z quotidien (PIZZA NAPOLI CARPENTRAS | AAAA-MM-JJ) »
contient les totaux du jour, le détail des ventes par produit, et des liens
de téléchargement (exports) valables 24 h.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup

from . import config

_TOTAUX = {
    "ca_ttc": r"CA TTC",
    "ca_ht": r"CA HT",
    "remises": r"Remises",
    "offerts": r"Offerts",
    "ticket_moyen": r"Ticket moyen",
    "corrections_avant": r"Corrections avant envoi en cuisine",
    "corrections_apres": r"Corrections après envoi en cuisine",
    "annulations": r"Annulations cuisine après ticket de caisse[^:]*",
}

# Libellé du lien dans le mail -> nom court utilisé pour le fichier archivé.
_EXPORTS = {
    "z digital": "z-digital",
    "export des ventes": "export-ventes",
    "export des lignes de ventes": "export-lignes-ventes",
    "export des règlements": "export-reglements",
    "export des annulations": "export-annulations",
}


@dataclass
class LigneVente:
    categorie: str
    produit: str
    quantite: float
    ttc: float
    ht: float


@dataclass
class Z:
    jour: date
    ca_ttc: float = 0.0
    ca_ht: float = 0.0
    remises: float = 0.0
    offerts: float = 0.0
    ticket_moyen: float = 0.0
    corrections_avant: float = 0.0
    corrections_apres: float = 0.0
    annulations: float = 0.0
    ventes: list[LigneVente] = field(default_factory=list)
    exports: dict[str, str] = field(default_factory=dict)   # nom court -> URL
    z_pdf: list[str] = field(default_factory=list)          # liens « Z » (un par service)

    @property
    def tickets(self) -> int:
        """Nombre de tickets estimé : CA TTC / ticket moyen."""
        return round(self.ca_ttc / self.ticket_moyen) if self.ticket_moyen else 0


def _nombre(texte: str) -> float | None:
    texte = texte.strip().replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return float(texte)
    except ValueError:
        return None


def date_depuis_objet(objet: str) -> date | None:
    m = re.search(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\)", objet)
    return date.fromisoformat(m.group(1)) if m else None


def lire_z(html: str, objet: str) -> Z:
    """Transforme le corps HTML du mail en objet Z. Lève ValueError si ce n'est pas un Z."""
    jour = date_depuis_objet(objet)
    if jour is None:
        raise ValueError(f"Objet de mail sans date de Z : {objet!r}")
    soup = BeautifulSoup(html, "html.parser")
    texte = soup.get_text("\n")
    z = Z(jour=jour)

    for nom, libelle in _TOTAUX.items():
        m = re.search(libelle + r"\s*:\s*(-?[\d\s.,]+)", texte)
        if m:
            setattr(z, nom, _nombre(m.group(1)) or 0.0)
    if not z.ca_ttc and "CA TTC" not in texte:
        raise ValueError("Aucun « CA TTC » dans le mail : format du Z non reconnu")

    # Tableau des ventes : Catégorie | Produit | QTE | TTC | HT
    for tr in soup.find_all("tr"):
        if tr.find("table"):
            continue   # ligne d'un tableau de mise en page qui contient d'autres tableaux
        cellules = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"], recursive=False)]
        if len(cellules) < 5:
            continue
        qte, ttc, ht = (_nombre(c) for c in cellules[-3:])
        if None in (qte, ttc, ht):
            continue   # ligne d'en-tête
        categorie = " ".join(cellules[-5].split())
        z.ventes.append(LigneVente(categorie, cellules[-4], qte, ttc, ht))

    # Liens : chaque « Télécharger » prend le libellé qui le précède.
    for a in soup.find_all("a"):
        if a.get_text(strip=True).lower() != "télécharger" or not a.get("href"):
            continue
        avant = a.find_previous(string=lambda s: s.strip() and s.strip().lower() != "télécharger")
        libelle = (avant or "").strip().lower()
        if libelle in _EXPORTS:
            z.exports[_EXPORTS[libelle]] = a["href"]
        elif libelle == "z":
            z.z_pdf.append(a["href"])
    return z


# --- Contrôles ---------------------------------------------------------------

@dataclass
class Alerte:
    gravite: str     # "haute" ou "info"
    titre: str
    detail: str


def _pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def _eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


def valeur_boissons_offertes(z: Z) -> tuple[int, float]:
    """Boissons de l'offre flyer passées à 0 € : nombre et valeur au prix de carte."""
    nb, valeur = 0, 0.0
    for v in z.ventes:
        prix = config.OFFRE_BOISSONS.get(v.produit.upper())
        if prix is not None and v.ttc == 0:
            nb += int(v.quantite)
            valeur += v.quantite * prix
    return nb, valeur


def controler(z: Z) -> list[Alerte]:
    """Contrôles de caisse d'une journée (sans historique)."""
    alertes: list[Alerte] = []
    if z.ca_ttc <= 0:
        return [Alerte("haute", "CA nul", f"Le Z du {z.jour:%d/%m} affiche un CA TTC de 0 €.")]

    part = z.annulations / z.ca_ttc
    if part > config.SEUIL_ANNULATIONS:
        alertes.append(Alerte(
            "haute", "Annulations après ticket de caisse",
            f"{_eur(z.annulations)}, soit {_pct(part)} du CA (seuil {_pct(config.SEUIL_ANNULATIONS)}). "
            "Détail dans l'export des annulations."))

    nb_boissons, val_boissons = valeur_boissons_offertes(z)
    offerts = z.offerts - (val_boissons if config.OFFERTS_INCLUENT_BOISSONS else 0.0)
    part = offerts / z.ca_ttc
    if part > config.SEUIL_OFFERTS:
        alertes.append(Alerte(
            "haute", "Offerts élevés",
            f"{_eur(offerts)} hors offre boissons, soit {_pct(part)} du CA "
            f"(seuil {_pct(config.SEUIL_OFFERTS)}). Boissons de l'offre flyer ce jour : {nb_boissons}."))

    corrections = z.corrections_avant + z.corrections_apres
    part = corrections / z.ca_ttc
    if part > config.SEUIL_CORRECTIONS:
        alertes.append(Alerte(
            "info", "Corrections élevées",
            f"{_eur(corrections)} de corrections (avant cuisine {_eur(z.corrections_avant)}, "
            f"après {_eur(z.corrections_apres)}), soit {_pct(part)} du CA."))
    return alertes


@dataclass
class JourHistorique:
    jour: date
    ca_ttc: float
    ticket_moyen: float


def controler_tendances(z: Z, historique: list[JourHistorique],
                        derniere_vente: dict[str, tuple[str, date]]) -> list[Alerte]:
    """Contrôles qui comparent la journée à l'historique (onglets Ventes du tableur).

    derniere_vente : produit -> (catégorie, date de dernière vente), hors journée z.
    """
    alertes: list[Alerte] = []
    par_jour = {h.jour: h for h in historique}

    semaine = par_jour.get(date.fromordinal(z.jour.toordinal() - 7))
    if semaine and semaine.ca_ttc > 0:
        ecart = (z.ca_ttc - semaine.ca_ttc) / semaine.ca_ttc
        if ecart < -config.SEUIL_BAISSE_CA:
            alertes.append(Alerte(
                "haute", "CA en baisse",
                f"{_eur(z.ca_ttc)} contre {_eur(semaine.ca_ttc)} le {semaine.jour:%A %d/%m} ({_pct(ecart)})."))

    mois = [h for h in historique if (h.jour.year, h.jour.month) == (z.jour.year, z.jour.month)
            and h.jour != z.jour and h.ticket_moyen > 0]
    if len(mois) >= 5:
        moyenne = sum(h.ticket_moyen for h in mois) / len(mois)
        ecart = (z.ticket_moyen - moyenne) / moyenne
        if ecart < -config.SEUIL_BAISSE_TICKET:
            alertes.append(Alerte(
                "info", "Ticket moyen en baisse",
                f"{_eur(z.ticket_moyen)} contre {_eur(moyenne)} en moyenne ce mois-ci ({_pct(ecart)})."))

    record_mois = all(z.ca_ttc > h.ca_ttc for h in mois) and len(mois) >= 5
    annee = [h for h in historique if h.jour.year == z.jour.year and h.jour != z.jour]
    if len(annee) >= 30 and all(z.ca_ttc > h.ca_ttc for h in annee):
        alertes.append(Alerte("info", "Record de l'année", f"Meilleur jour de {z.jour.year} : {_eur(z.ca_ttc)}."))
    elif record_mois:
        alertes.append(Alerte("info", "Record du mois", f"Meilleur jour du mois : {_eur(z.ca_ttc)}."))

    if historique and (z.jour - min(h.jour for h in historique)).days >= config.JOURS_SANS_VENTE:
        vendus = {v.produit for v in z.ventes}
        oubliees = sorted(
            p for p, (cat, d) in derniere_vente.items()
            if p not in vendus and cat.upper() not in config.CATEGORIES_HORS_PIZZA
            and (z.jour - d).days >= config.JOURS_SANS_VENTE)
        if oubliees:
            alertes.append(Alerte(
                "info", "Pizzas qui ne se vendent plus",
                f"Aucune vente depuis {config.JOURS_SANS_VENTE} jours ou plus : {', '.join(oubliees)}."))
    return alertes
