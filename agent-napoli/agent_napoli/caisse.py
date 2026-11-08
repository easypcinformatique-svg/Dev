"""Archivage du Z et historique des ventes.

Les liens d'export du mail L'Addition expirent au bout de 24 h : l'agent les
télécharge le matin même dans Drive « Pizza Napoli/Caisse/AAAA-MM/ », puis
inscrit les chiffres du jour dans les onglets « Ventes » et « Ventes produits ».
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date

from . import config
from .outils import lire_date, lire_nombre
from .z_laddition import JourHistorique, Z

_EXT = {"text/csv": "csv", "application/pdf": "pdf", "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/json": "json"}


def _nombre(x) -> float:
    return lire_nombre(x) or 0.0


def _telecharger(url: str) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "agent-pizza-napoli"})
    with urllib.request.urlopen(req, timeout=60) as r:
        donnees = r.read()
        mime = r.headers.get_content_type()
        dispo = r.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', dispo)
    ext = m.group(1).rsplit(".", 1)[-1].lower() if m and "." in m.group(1) else _EXT.get(mime, "bin")
    return donnees, mime, ext


def archiver(g, z: Z) -> list[str]:
    """Télécharge les exports du Z dans Drive. Renvoie les erreurs éventuelles."""
    dossier = g.dossier("Caisse", f"{z.jour:%Y-%m}")
    erreurs = []
    liens = dict(z.exports)
    for i, url in enumerate(z.z_pdf, 1):
        liens[f"z-service-{i}"] = url
    for nom, url in liens.items():
        try:
            donnees, mime, ext = _telecharger(url)
        except OSError as e:
            erreurs.append(f"{nom} : téléchargement impossible ({e})")
            continue
        g.deposer(dossier, f"{z.jour.isoformat()}_{nom}.{ext}", donnees, mime)
    return erreurs


def deja_enregistre(lignes_ventes: list[list[str]], jour: date) -> bool:
    return any(l and lire_date(l[0]) == jour for l in lignes_ventes)


def enregistrer(g, z: Z, lignes_ventes: list[list[str]]) -> bool:
    """Inscrit le Z dans le tableur, une seule fois par jour. Renvoie True si inscrit."""
    if deja_enregistre(lignes_ventes, z.jour):
        return False
    g.ajouter("Ventes", [[z.jour.isoformat(), z.ca_ttc, z.ca_ht, z.ticket_moyen, z.tickets, z.offerts,
                          z.corrections_avant, z.corrections_apres, z.annulations]])
    g.ajouter("Ventes produits", [[z.jour.isoformat(), v.categorie, v.produit, v.quantite, v.ttc, v.ht]
                                  for v in z.ventes])
    lignes_ventes.append([z.jour.isoformat()])
    return True


def historique(lignes_ventes: list[list[str]]) -> list[JourHistorique]:
    res = []
    for l in lignes_ventes:
        if len(l) < 4:
            continue
        d = lire_date(l[0])
        if d:
            res.append(JourHistorique(d, _nombre(l[1]), _nombre(l[3])))
    return res


def dernieres_ventes(lignes_produits: list[list[str]], avant: date) -> dict[str, tuple[str, date]]:
    """Produit -> (catégorie, dernier jour de vente), en ne regardant que les jours avant `avant`."""
    res: dict[str, tuple[str, date]] = {}
    for l in lignes_produits:
        if len(l) < 4 or _nombre(l[3]) <= 0:
            continue
        d = lire_date(l[0])
        if d and d < avant and (l[2] not in res or res[l[2]][1] < d):
            res[l[2]] = (l[1], d)
    return res


def top_produits(z: Z, n: int = 5) -> list[tuple[str, float]]:
    pizzas = [v for v in z.ventes if v.categorie.upper() not in config.CATEGORIES_HORS_PIZZA]
    return [(v.produit, v.quantite) for v in sorted(pizzas, key=lambda v: (-v.quantite, -v.ttc))[:n]]
