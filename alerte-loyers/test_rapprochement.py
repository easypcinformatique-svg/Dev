"""Tests du rapprochement (noms fictifs). Lancer : python -m unittest -v"""
import unittest
from datetime import date
from decimal import Decimal

from alerte_loyers import rediger
from rapprochement import MANQUANT, PARTIEL, RECU, Virement, charger_baux, rapprocher, virement_depuis_transaction

BAUX = charger_baux({"baux": [
    {"nom": "T2 A", "montant": 800, "payeurs": ["DUPONT", "CAF"]},
    {"nom": "T2 B", "montant": 800, "payeurs": ["MARTIN"]},
    {"nom": "Local", "montant": 651.40, "payeurs": ["L'Instant Coiffure"]},
    {"nom": "Villa", "montant": 1200, "payeurs": ["DURAND"]},
]})


def tx(montant, libelle, sens="CRDT", date_="2026-10-05", ref=None):
    return {"credit_debit_indicator": sens, "booking_date": date_, "entry_reference": ref,
            "transaction_amount": {"amount": str(montant), "currency": "EUR"},
            "remittance_information": [libelle]}


def statuts(virements):
    return {r.bail.nom: r.statut for r in rapprocher(BAUX, virements)}


class TestRapprochement(unittest.TestCase):
    def test_mois_complet_avec_paiement_en_deux_fois_et_caf(self):
        virements = [virement_depuis_transaction(t) for t in [
            tx(304, "VIR CAF BOUCHES DU RHONE"),
            tx("651.40", "VIR L'INSTANT COIFFURE LOYER"),
            tx(1200, "VIR INST MONSIEUR DURAND JEAN"),
            tx(496, "VIR DUPONT LEA VIREMENT AVEC FORTUNEO", date_="2026-10-06"),
            tx(650, "VIR MME MARTIN ANNE", date_="2026-10-08"),
            tx(3000, "VIR PIZZA CARPENTRAS", date_="2026-10-13"),
            tx(150, "VIR DE MME MARTIN ANNE", date_="2026-10-14"),
        ]]
        resultats = rapprocher(BAUX, virements)
        self.assertEqual({r.statut for r in resultats}, {RECU})
        self.assertEqual(resultats[0].total, Decimal("800"))
        self.assertEqual(len(resultats[1].virements), 2)

    def test_partiel_quand_la_caf_ne_verse_pas(self):
        virements = [virement_depuis_transaction(tx(496, "VIR DUPONT LEA"))]
        resultat = rapprocher(BAUX, virements)[0]
        self.assertEqual(resultat.statut, PARTIEL)
        self.assertEqual(resultat.manque, Decimal("304"))

    def test_manquant(self):
        self.assertEqual(statuts([])["Villa"], MANQUANT)

    def test_debits_ignores(self):
        self.assertIsNone(virement_depuis_transaction(tx(1200, "DURAND", sens="DBIT")))

    def test_mots_entiers_et_accents(self):
        v = virement_depuis_transaction(tx(800, "Vir Café Dupontel"))
        self.assertEqual(statuts([v])["T2 A"], MANQUANT)
        v = virement_depuis_transaction(tx(800, "Vir M. Dùpont"))
        self.assertEqual(statuts([v])["T2 A"], RECU)

    def test_nom_de_l_emetteur_utilise(self):
        t = tx(1200, "LOYER OCTOBRE")
        t["debtor"] = {"name": "Jean Durand"}
        self.assertEqual(statuts([virement_depuis_transaction(t)])["Villa"], RECU)

    def test_tolerance_centimes(self):
        v = Virement("2026-10-05", Decimal("799.50"), "DUPONT")
        self.assertEqual(statuts([v])["T2 A"], RECU)


class TestMessage(unittest.TestCase):
    def test_message_avec_probleme(self):
        virements = [Virement("2026-10-06", Decimal("496"), "DUPONT")]
        titre, corps, probleme = rediger(rapprocher(BAUX, virements), [], date(2026, 10, 1))
        self.assertTrue(probleme)
        self.assertIn("octobre 2026", titre)
        self.assertIn("il manque 304,00 €", corps)
        self.assertIn("❌ Villa : rien reçu (attendu 1 200,00 €)", corps)

    def test_message_tout_recu(self):
        virements = [Virement("2026-10-05", b.montant, b.payeurs[0]) for b in BAUX]
        titre, _, probleme = rediger(rapprocher(BAUX, virements), [], date(2026, 10, 1))
        self.assertFalse(probleme)
        self.assertEqual(titre, "✅ Loyers octobre 2026 : 4/4 reçus")


if __name__ == "__main__":
    unittest.main()
