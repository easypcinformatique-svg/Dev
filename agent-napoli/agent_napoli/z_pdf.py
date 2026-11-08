"""Lecture du ticket Z en PDF (lien « Z » du mail L'Addition).

Le PDF contient ce que le mail n'a pas : la répartition par salle (livraison,
à emporter, sur place), les moyens de paiement et le nombre exact de tickets.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import parse_qs, urlparse

from .outils import lire_nombre

_LIGNE_MONTANT = re.compile(r"^(?:\(x(\d+)\)\s*)?(.+?)\s+(-?[\d\s.]*\d,\d{2})$")


@dataclass
class DetailZ:
    salles: dict[str, float] = field(default_factory=dict)            # Livraison -> 537.20
    reglements: dict[str, tuple[int, float]] = field(default_factory=dict)   # CB -> (32, 875.0)
    tickets: int | None = None


def date_du_lien(url: str) -> date | None:
    q = parse_qs(urlparse(url).query)
    try:
        return date.fromisoformat(q["date_start"][0])
    except (KeyError, ValueError):
        return None


def liens_du_jour(liens: list[str], jour: date) -> list[str]:
    """Les liens « Z » dont la période commence le jour donné ; tous si aucun n'est daté."""
    dates = [date_du_lien(u) for u in liens]
    if not any(dates):
        return list(liens)
    return [u for u, d in zip(liens, dates) if d == jour]


def lire_texte(texte: str) -> DetailZ:
    detail = DetailZ()
    section = None
    for brut in texte.splitlines():
        ligne = " ".join(brut.split())
        if ligne == "CA par salle":
            section = "salles"
            continue
        if ligne == "Règlements du service":
            section = "reglements"
            continue
        if ligne in ("Total règlements", "Menus") or ligne.startswith("Imprimé le"):
            section = None
            continue
        m = _LIGNE_MONTANT.match(ligne)
        if not m or section is None:
            continue
        nombre, libelle, montant = m.group(1), m.group(2).strip(), lire_nombre(m.group(3))
        if montant is None:
            continue
        if section == "salles":
            detail.salles[libelle] = montant
        elif libelle == "Total CA TTC":
            detail.tickets = int(nombre) if nombre else None
        else:
            detail.reglements[libelle] = (int(nombre) if nombre else 0, montant)
    return detail


def lire_pdf(donnees: bytes) -> DetailZ:
    from pypdf import PdfReader
    lecteur = PdfReader(io.BytesIO(donnees))
    return lire_texte("\n".join(page.extract_text() or "" for page in lecteur.pages))
