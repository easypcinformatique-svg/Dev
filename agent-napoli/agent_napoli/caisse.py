"""Archivage du Z et historique des ventes.

Les liens d'export du mail L'Addition expirent au bout de 24 h : l'agent les
télécharge le matin même dans Drive « Pizza Napoli/Caisse/AAAA-MM/ », puis
inscrit les chiffres du jour dans les onglets « Ventes » et « Ventes produits ».
"""

from __future__ import annotations

import re
import urllib.request
from datetime import date

from . import config, z_pdf
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


def archiver(g, z: Z) -> tuple[list[str], z_pdf.DetailZ | None]:
    """Télécharge dans Drive les exports et le ticket Z du jour, et lit ce dernier.

    Le mail contient une trentaine de liens « Z » ; seuls ceux du jour du Z sont gardés.
    Renvoie les erreurs éventuelles et le détail lu dans le PDF (salles, paiements).
    """
    dossier = g.dossier("Caisse", f"{z.jour:%Y-%m}")
    erreurs, detail = [], None
    liens = dict(z.exports)
    for i, url in enumerate(z_pdf.liens_du_jour(z.z_pdf, z.jour), 1):
        liens[f"z-{i}"] = url
    for nom, url in liens.items():
        try:
            donnees, mime, ext = _telecharger(url)
        except OSError as e:
            erreurs.append(f"{nom} : téléchargement impossible ({e})")
            continue
        g.deposer(dossier, f"{z.jour.isoformat()}_{nom}.{ext}", donnees, mime)
        if nom.startswith("z-") and detail is None and donnees[:4] == b"%PDF":
            try:
                detail = z_pdf.lire_pdf(donnees)
            except Exception as e:   # PDF illisible : on garde l'archive, on le signale
                erreurs.append(f"{nom} : lecture du PDF impossible ({e})")
    return erreurs, detail


def deja_enregistre(lignes_ventes: list[list[str]], jour: date) -> bool:
    return any(l and lire_date(l[0]) == jour for l in lignes_ventes)


def ligne_vente(z: Z, detail: z_pdf.DetailZ | None) -> list:
    tickets = detail.tickets if detail and detail.tickets else z.tickets
    complement = ([z_pdf.total_cb(detail), z_pdf.salle(detail, "livraison"), z_pdf.salle(detail, "emporter")]
                  if detail else ["", "", ""])
    return [z.jour.isoformat(), z.ca_ttc, z.ca_ht, z.ticket_moyen, tickets, z.offerts,
            z.corrections_avant, z.corrections_apres, z.annulations,
            *["" if v is None else v for v in complement]]


def lignes_produits(z: Z) -> list[list]:
    return [[z.jour.isoformat(), v.categorie, v.produit, v.quantite, v.ttc, v.ht] for v in z.ventes]


def enregistrer(g, z: Z, lignes_ventes: list[list[str]], detail: z_pdf.DetailZ | None = None) -> bool:
    """Inscrit le Z dans le tableur, une seule fois par jour. Renvoie True si inscrit."""
    if deja_enregistre(lignes_ventes, z.jour):
        return False
    ligne = ligne_vente(z, detail)
    g.ajouter("Ventes", [ligne])
    g.ajouter("Ventes produits", lignes_produits(z))
    lignes_ventes.append(ligne)
    return True


def rattraper_historique(g, journal, telecharger_pdf: bool = True) -> int:
    """Relit une fois tous les anciens mails de Z et remplit les onglets Ventes.

    Sans IA (gratuit). Les jours déjà présents sont ignorés. Les exports ne sont pas
    archivés ; le PDF du Z du jour est seulement lu (livraison, paiements) s'il est
    encore téléchargeable. Écrit par lots pour respecter les quotas de Google Sheets.
    """
    from .z_laddition import lire_z
    connus = {lire_date(l[0]) for l in g.lignes("Ventes") if l}
    ventes, produits, lus = [], [], 0
    for id_ in g.chercher(f'from:{config.Z_EXPEDITEUR} subject:"{config.Z_OBJET}"', maximum=5000):
        msg = g.lire(id_)
        try:
            z = lire_z(msg.html or msg.texte, msg.objet)
        except ValueError:
            continue
        if z.jour in connus:
            continue
        detail = None
        if telecharger_pdf:
            for url in z_pdf.liens_du_jour(z.z_pdf, z.jour)[:1]:
                try:
                    donnees, _, _ = _telecharger(url)
                    if donnees[:4] == b"%PDF":
                        detail = z_pdf.lire_pdf(donnees)
                except Exception:      # lien expiré ou PDF illisible : on garde les chiffres du mail
                    pass
        ventes.append(ligne_vente(z, detail))
        produits += lignes_produits(z)
        connus.add(z.jour)
        lus += 1
    ventes.sort(key=lambda l: l[0])
    for i in range(0, len(ventes), 500):
        g.ajouter("Ventes", ventes[i:i + 500])
    produits.sort(key=lambda l: l[0])
    for i in range(0, len(produits), 2000):
        g.ajouter("Ventes produits", produits[i:i + 2000])
    journal("historique", "Z relus", f"{lus} jour(s) ajouté(s)")
    return lus


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
