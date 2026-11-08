"""Relevé de compte mensuel et rapprochement, avant le dépôt Cegid pour la TVA.

Un gérant dépose le relevé (PDF, CSV ou Excel) dans Drive
« Pizza Napoli/Banque/À traiter ». Au passage suivant, l'agent :
- recopie les opérations dans l'onglet « Banque » du tableur ;
- passe à « payée » chaque facture dont le montant correspond à un débit ;
- liste les débits sans facture : les pièces à retrouver avant la TVA ;
- compare les remises CB du relevé aux paiements CB des tickets Z du mois ;
- range le relevé dans « Banque/AAAA-MM » et l'ajoute, avec le tableau de
  rapprochement, au dossier Cegid du mois.
"""

from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape

from . import comptable, config, ia
from .factures import COL as COL_F, _slug
from .outils import lire_date, lire_nombre

TYPES_TABLEUR = {
    "text/csv": "csv", "text/plain": "csv", "application/vnd.ms-excel": "csv",
    "application/vnd.google-apps.spreadsheet": "csv",   # converti par Drive : exporté en CSV
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
}
TYPES_ACCEPTES = {"application/pdf", *TYPES_TABLEUR}
TOLERANCE = 0.01                 # écart de montant accepté (euros)
FENETRE = (-7, 90)               # débit entre 7 jours avant et 90 jours après la date de facture
_SANS_PIECE = {"frais_bancaires", "remise_cb", "especes"}   # pas de facture attendue
_MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
         "septembre", "octobre", "novembre", "décembre"]


@dataclass
class Operation:
    jour: date
    libelle: str
    montant: float
    type: str


def _eur(x: float) -> str:
    return f"{x:,.2f} €".replace(",", " ").replace(".", ",")


def texte_tableur(donnees: bytes, sorte: str) -> str:
    """CSV ou Excel -> texte « ; » lisible par Claude."""
    if sorte == "xlsx":
        from openpyxl import load_workbook
        classeur = load_workbook(io.BytesIO(donnees), read_only=True, data_only=True)
        lignes = []
        for feuille in classeur.worksheets:
            for rangee in feuille.iter_rows(values_only=True):
                if any(c is not None for c in rangee):
                    lignes.append(";".join("" if c is None else str(c) for c in rangee))
        return "\n".join(lignes)
    for codage in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return donnees.decode(codage)
        except UnicodeDecodeError:
            continue
    return donnees.decode("latin-1", "replace")


def operations(releve: dict) -> list[Operation]:
    res = []
    for o in releve.get("operations", []):
        d = lire_date(o.get("date"))
        if d is not None:
            res.append(Operation(d, o.get("libelle", ""), float(o.get("montant") or 0), o.get("type", "autre")))
    return res


def mois_du_releve(releve: dict, ops: list[Operation]) -> tuple[int, int] | None:
    d = lire_date(releve.get("periode_debut"))
    if d:
        return d.year, d.month
    if not ops:
        return None
    return Counter((o.jour.year, o.jour.month) for o in ops).most_common(1)[0][0]


def verifier_soldes(releve: dict, ops: list[Operation]) -> str | None:
    """Contrôle de complétude : solde initial + opérations = solde final."""
    ini, fin = releve.get("solde_initial"), releve.get("solde_final")
    if ini is None or fin is None:
        return None
    ecart = round(ini + sum(o.montant for o in ops) - fin, 2)
    if abs(ecart) > TOLERANCE:
        return (f"les opérations lues ne retombent pas sur le solde final (écart {_eur(ecart)}) : "
                "une ligne a pu être mal lue, vérifiez le relevé")
    return None


def _nom_correspond(fournisseur: str, libelle: str) -> bool:
    lib = _slug(libelle).lower()
    return any(len(mot) >= 4 and mot in lib for mot in _slug(fournisseur).lower().split("-"))


@dataclass
class Rapprochement:
    appariements: list[tuple[Operation, int]] = field(default_factory=list)   # (débit, ligne facture)
    sans_piece: list[Operation] = field(default_factory=list)


def rapprocher(ops: list[Operation], lignes_factures: list[list[str]]) -> Rapprochement:
    """Associe chaque débit à au plus une facture de même montant TTC, et réciproquement."""
    factures = []
    for i, l in enumerate(lignes_factures):
        l = l + [""] * (len(COL_F) - len(l))
        ttc = lire_nombre(l[COL_F["TTC"]])
        if ttc is not None:
            factures.append((i, l[COL_F["Fournisseur"]], abs(ttc),
                             lire_date(l[COL_F["Date facture"]]) or lire_date(l[COL_F["Reçue le"]])))
    prises: set[int] = set()
    res = Rapprochement()
    for op in sorted((o for o in ops if o.montant < 0), key=lambda o: o.jour):
        candidats = []
        for i, fournisseur, ttc, d in factures:
            if i in prises or abs(ttc - (-op.montant)) > TOLERANCE:
                continue
            if d and not (d + timedelta(days=FENETRE[0]) <= op.jour <= d + timedelta(days=FENETRE[1])):
                continue
            ecart_jours = abs((op.jour - d).days) if d else 999
            candidats.append((0 if _nom_correspond(fournisseur, op.libelle) else 1, ecart_jours, i))
        if candidats:
            i = min(candidats)[2]
            prises.add(i)
            res.appariements.append((op, i))
        elif op.type not in _SANS_PIECE:
            res.sans_piece.append(op)
    return res


def controle_cb(ops: list[Operation], lignes_ventes: list[list[str]], annee: int, mois: int) -> tuple[float, float]:
    """(paiements CB selon les tickets Z du mois, remises CB créditées sur le relevé)."""
    col = config.ONGLETS["Ventes"].index("CB (Z)")
    cb_z = 0.0
    for l in lignes_ventes:
        d = lire_date(l[0]) if l else None
        if d and (d.year, d.month) == (annee, mois) and len(l) > col:
            cb_z += lire_nombre(l[col]) or 0.0
    cb_banque = sum(o.montant for o in ops if o.type == "remise_cb" and o.montant > 0)
    return round(cb_z, 2), round(cb_banque, 2)


@dataclass
class BilanReleve:
    nom: str
    lignes_rapport: list[str] = field(default_factory=list)
    erreurs: list[str] = field(default_factory=list)
    mois: str | None = None


def _csv_rapprochement(ops: list[Operation], r: Rapprochement, lignes_factures) -> bytes:
    lien = {id(op): lignes_factures[i] for op, i in r.appariements}
    manquantes = {id(op) for op in r.sans_piece}
    f = io.StringIO()
    w = csv.writer(f, delimiter=";")
    w.writerow(["Date", "Libellé", "Montant", "Type", "Rapprochement"])
    for op in ops:
        if id(op) in lien:
            l = lien[id(op)]
            etat = f"facture {l[COL_F['Fournisseur']]} n° {l[COL_F['N° facture']]}".strip()
        elif id(op) in manquantes:
            etat = "PIÈCE MANQUANTE"
        else:
            etat = ""
        w.writerow([op.jour.isoformat(), op.libelle, f"{op.montant:.2f}".replace(".", ","), op.type, etat])
    return f.getvalue().encode("utf-8-sig")


def traiter_releve(g, nom: str, donnees: bytes, type_mime: str, lignes_factures, lignes_ventes,
                   id_drive: str | None = None) -> BilanReleve:
    bilan = BilanReleve(nom)
    sorte = TYPES_TABLEUR.get(type_mime)
    try:
        releve = ia.lire_releve(donnees, type_mime, texte_tableur(donnees, sorte) if sorte else None)
    except ia.ErreurIA as e:
        bilan.erreurs.append(f"Relevé « {nom} » : lecture impossible ({e}), nouvel essai demain")
        return bilan
    if not releve.get("est_un_releve"):
        bilan.erreurs.append(f"« {nom} » ne ressemble pas à un relevé de compte : laissé dans « À traiter »")
        return bilan
    ops = operations(releve)
    periode = mois_du_releve(releve, ops)
    if periode is None:
        bilan.erreurs.append(f"Relevé « {nom} » : aucune opération lue")
        return bilan
    annee, mois = periode
    bilan.mois = f"{annee}-{mois:02d}"
    nom_mois = f"{_MOIS[mois - 1]} {annee}"

    alerte_soldes = verifier_soldes(releve, ops)
    r = rapprocher(ops, lignes_factures)
    payees = 0
    for _, i in r.appariements:
        l = lignes_factures[i] + [""] * (len(COL_F) - len(lignes_factures[i]))
        if l[COL_F["Statut"]].strip().lower() != "payée":
            g.ecrire_cellule("Factures", i, COL_F["Statut"], "payée")
            payees += 1

    # Tableur, archives, dossier Cegid
    g.ajouter("Banque", [[o.jour.isoformat(), o.libelle, o.montant, o.type, bilan.mois] for o in ops])
    ext = "pdf" if type_mime == "application/pdf" else sorte
    nom_archive = f"releve_{bilan.mois}_{_slug(releve.get('banque') or 'banque')}.{ext}"
    dossier_banque = g.dossier("Banque", bilan.mois)
    if id_drive:
        g.deplacer(id_drive, dossier_banque, nom_archive)
    else:
        g.deposer(dossier_banque, nom_archive, donnees, type_mime)
    cegid = g.dossier("Comptable", comptable.nom_dossier(annee, mois))
    g.deposer(cegid, nom_archive, donnees, "text/csv" if type_mime.startswith("application/vnd.google-apps") else type_mime)
    g.deposer(cegid, f"rapprochement_{bilan.mois}.csv", _csv_rapprochement(ops, r, lignes_factures), "text/csv")

    # Phrases du rapport
    lignes = [f"Relevé de {nom_mois} traité : {len(ops)} opérations, {payees} facture(s) passée(s) à « payée », "
              f"rangé avec le rapprochement dans le dossier Cegid."]
    if alerte_soldes:
        bilan.erreurs.append(f"Relevé de {nom_mois} : {alerte_soldes}")
    if r.sans_piece:
        total = sum(-o.montant for o in r.sans_piece)
        details = "; ".join(f"{o.jour:%d/%m} {escape(o.libelle)} {_eur(o.montant)}" for o in r.sans_piece[:15])
        reste = f" (+{len(r.sans_piece) - 15} autres, voir rapprochement_{bilan.mois}.csv)" if len(r.sans_piece) > 15 else ""
        lignes.append(f"<b>{len(r.sans_piece)} débit(s) sans facture ({_eur(total)})</b>, pièces à retrouver "
                      f"avant la TVA : {details}{reste}.")
    else:
        lignes.append("Tous les débits ont leur facture.")
    cb_z, cb_banque = controle_cb(ops, lignes_ventes, annee, mois)
    if cb_z or cb_banque:
        ecart = cb_banque - cb_z
        lignes.append(f"Cartes bancaires : {_eur(cb_z)} encaissés selon les tickets Z, {_eur(cb_banque)} de remises CB "
                      f"sur le relevé (écart {_eur(ecart)}). Un petit écart vient souvent des remises des derniers "
                      "jours, créditées le mois suivant.")
    bilan.lignes_rapport = lignes
    return bilan


def traiter_dossier(g, lignes_factures, lignes_ventes) -> list[BilanReleve]:
    dossier = g.dossier("Banque", config.DOSSIER_A_TRAITER)
    bilans = []
    for f in g.lister(dossier):
        if f["mimeType"] not in TYPES_ACCEPTES:
            bilans.append(BilanReleve(f["name"], erreurs=[
                f"« {f['name']} » : format non pris en charge pour un relevé (PDF, CSV ou Excel)"]))
            continue
        bilans.append(traiter_releve(g, f["name"], g.telecharger(f["id"], f["mimeType"]), f["mimeType"],
                                     lignes_factures, lignes_ventes, id_drive=f["id"]))
    return bilans
