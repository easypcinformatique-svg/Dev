"""Relevé de compte et rapprochement. Chiffres et fournisseurs fictifs."""

import io
from datetime import date

import pytest

from agent_napoli import banque, config, ia
from agent_napoli.banque import Operation
from conftest import FauxGoogle


def facture(fournisseur, numero, jour, ttc, statut="à payer"):
    return ["2026-10-01", fournisseur, numero, jour, "", "", "", ttc, statut, "", f"https://drive.google.com/file/d/{numero}/view", ""]


FACTURES = [
    facture("Metro Avignon", "M1", "2026-10-03", "412,80"),
    facture("Grossiste Fromages", "G1", "2026-10-05", "180,00"),
    facture("Laiterie du Sud", "L1", "2026-10-06", "180,00"),
    facture("EDF Pro", "E1", "2026-09-28", "96,10", statut="payée"),
    facture("Vieux fournisseur", "V1", "2026-03-01", "55,00"),
]


def op(jour, libelle, montant, type_="prelevement"):
    return Operation(date.fromisoformat(jour), libelle, montant, type_)


def test_rapprochement():
    ops = [
        op("2026-10-04", "CB METRO AVIGNON", -412.80, "carte"),
        op("2026-10-10", "PRLV LAITERIE DU SUD", -180.00),   # même montant que Grossiste : le nom départage
        op("2026-10-12", "VIR GROSSISTE FROMAGES", -180.00, "virement_emis"),
        op("2026-10-02", "PRLV EDF", -96.10),                  # facture déjà payée : rapprochée quand même
        op("2026-10-15", "PRLV INCONNU SARL", -64.00),          # aucune facture : pièce manquante
        op("2026-10-20", "PRLV ANCIEN", -55.00),                # facture de mars : hors fenêtre de 90 jours
        op("2026-10-31", "FRAIS TENUE DE COMPTE", -12.00, "frais_bancaires"),
        op("2026-10-05", "REMISE CB 0510", 850.00, "remise_cb"),
    ]
    r = banque.rapprocher(ops, FACTURES)
    lien = {o.libelle: FACTURES[i][1] for o, i in r.appariements}
    assert lien == {"CB METRO AVIGNON": "Metro Avignon", "PRLV LAITERIE DU SUD": "Laiterie du Sud",
                    "VIR GROSSISTE FROMAGES": "Grossiste Fromages", "PRLV EDF": "EDF Pro"}
    assert [o.libelle for o in r.sans_piece] == ["PRLV INCONNU SARL", "PRLV ANCIEN"]


def test_une_facture_ne_sert_qu_une_fois():
    ops = [op("2026-10-04", "CB METRO", -412.80, "carte"), op("2026-10-09", "CB METRO", -412.80, "carte")]
    r = banque.rapprocher(ops, FACTURES)
    assert len(r.appariements) == 1 and len(r.sans_piece) == 1


def test_controle_des_soldes():
    ops = [op("2026-10-04", "A", -100.0), op("2026-10-05", "B", 250.0)]
    assert banque.verifier_soldes({"solde_initial": 1000, "solde_final": 1150}, ops) is None
    assert "écart" in banque.verifier_soldes({"solde_initial": 1000, "solde_final": 1200}, ops)
    assert banque.verifier_soldes({"solde_initial": None, "solde_final": 1}, ops) is None


def test_controle_cb():
    col = config.ONGLETS["Ventes"].index("CB (Z)")
    def vente(jour, cb):
        l = [jour] + [""] * (col - 1) + [cb]
        return l
    ventes = [vente("2026-10-01", "500"), vente("02/10/2026", "300,50"), vente("2026-11-01", "999")]
    ops = [op("2026-10-02", "REMISE CB", 500.0, "remise_cb"), op("2026-10-03", "REMISE CB", 290.0, "remise_cb")]
    assert banque.controle_cb(ops, ventes, 2026, 10) == (800.5, 790.0)


def test_lecture_csv_et_excel():
    assert banque.texte_tableur("Date;Libellé\n01/10/2026;Café".encode("cp1252"), "csv").startswith("Date;Libellé")
    from openpyxl import Workbook
    wb = Workbook()
    wb.active.append(["Date", "Libellé", "Montant"])
    wb.active.append(["01/10/2026", "PRLV EDF", -96.1])
    tampon = io.BytesIO()
    wb.save(tampon)
    assert banque.texte_tableur(tampon.getvalue(), "xlsx") == "Date;Libellé;Montant\n01/10/2026;PRLV EDF;-96.1"


RELEVE = {
    "est_un_releve": True, "banque": "Banque Exemple", "periode_debut": "2026-10-01", "periode_fin": "2026-10-31",
    "solde_initial": 5000.0, "solde_final": 5193.20,
    "operations": [
        {"date": "2026-10-04", "libelle": "CB METRO AVIGNON", "montant": -412.80, "type": "carte"},
        {"date": "2026-10-15", "libelle": "PRLV INCONNU <SARL>", "montant": -64.00, "type": "prelevement"},
        {"date": "2026-10-05", "libelle": "REMISE CB", "montant": 670.00, "type": "remise_cb"},
    ],
}


@pytest.fixture
def releve_factice(monkeypatch):
    appels = []
    def lire_releve(donnees, mime, texte=None):
        appels.append((mime, texte))
        return dict(RELEVE)
    monkeypatch.setattr(ia, "lire_releve", lire_releve)
    return appels


def test_traitement_complet_du_releve(releve_factice):
    g = FauxGoogle(fichiers_a_traiter=[{"id": "R1", "name": "releve octobre.csv", "mimeType": "text/csv"}])
    g.contenus_drive["R1"] = "Date;Libellé;Montant\n04/10/2026;CB METRO AVIGNON;-412,80".encode()
    col = config.ONGLETS["Ventes"].index("CB (Z)")
    ventes = [["2026-10-04"] + [""] * (col - 1) + ["700"]]
    (b,) = banque.traiter_dossier(g, [list(l) for l in FACTURES], ventes)

    assert releve_factice[0][1].startswith("Date;Libellé;Montant")      # CSV converti en texte
    assert b.mois == "2026-10" and not b.erreurs
    assert ("Factures", 0, 8, "payée") in g.cellules                      # Metro passée à payée
    assert len(g.ajouts["Banque"]) == 3
    assert g.deplacements == [("R1", "Banque/2026-10", "releve_2026-10_Banque-Exemple.csv")]
    cegid = "Comptable/2026-10 à déposer sur Cegid"
    assert [(d, n) for d, n in g.depots] == [(cegid, "releve_2026-10_Banque-Exemple.csv"),
                                             (cegid, "rapprochement_2026-10.csv")]
    texte = " ".join(b.lignes_rapport)
    assert "3 opérations, 1 facture(s) passée(s) à « payée »" in texte
    assert "1 débit(s) sans facture (64,00 €)" in texte and "PRLV INCONNU &lt;SARL&gt;" in texte
    assert "700,00 € encaissés selon les tickets Z, 670,00 € de remises CB" in texte


def test_solde_incoherent_signale(releve_factice, monkeypatch):
    monkeypatch.setattr(ia, "lire_releve", lambda *a, **k: {**RELEVE, "solde_final": 9999.0})
    b = banque.traiter_releve(FauxGoogle(), "r.pdf", b"%PDF", "application/pdf", [], [])
    assert "ne retombent pas sur le solde final" in b.erreurs[0]


def test_document_qui_n_est_pas_un_releve(monkeypatch):
    monkeypatch.setattr(ia, "lire_releve", lambda *a, **k: {**RELEVE, "est_un_releve": False})
    g = FauxGoogle()
    b = banque.traiter_releve(g, "menu.pdf", b"%PDF", "application/pdf", [], [], id_drive="X")
    assert b.mois is None and "ne ressemble pas" in b.erreurs[0] and not g.deplacements
