"""Lecture du ticket Z en PDF. Chiffres fictifs, même mise en forme que le PDF de L'Addition."""

from datetime import date

from agent_napoli import rapport, z_pdf
from agent_napoli.z_laddition import Z

TEXTE = """PIZZERIA EXEMPLE
Rapport Z du Du 2026-03-03 17:30:00 au
2026-03-03 22:40:00
Total HT 900,00
Total TTC 1 000,00
Offerts (2.0% du total) 20,00
CA par catégories
(x10) LES CLASSIQUES 120,00
_ (x10) REINE 120,00
Menus
CA par salle
Livraison 600,00
A Emporter 350,00
Sur place 50,00
Règlements du service
(x30) CB 700,00
(x8) Espèces 200,00
(x2) Ticket restaurant 100,00
(x40) Total CA TTC 1 000,00
Total règlements
(x30) CB 700,00
Imprimé le 04/03/2026 à 09:00
v1
"""


def test_lecture_du_texte_du_pdf():
    d = z_pdf.lire_texte(TEXTE)
    assert d.salles == {"Livraison": 600.0, "A Emporter": 350.0, "Sur place": 50.0}
    assert d.reglements == {"CB": (30, 700.0), "Espèces": (8, 200.0), "Ticket restaurant": (2, 100.0)}
    assert d.tickets == 40


def test_seuls_les_liens_z_du_jour_sont_gardes():
    base = "https://data.laddition.com/scripts/reporting/v1/Z.php?db=x&signature=s"
    liens = [f"{base}&date_start=2026-03-0{j}&date_end=2026-03-0{j}" for j in (1, 2, 3)]
    assert z_pdf.liens_du_jour(liens, date(2026, 3, 3)) == [liens[2]]
    assert z_pdf.liens_du_jour(["https://x/a", "https://x/b"], date(2026, 3, 3)) == ["https://x/a", "https://x/b"]


def test_rapport_avec_le_detail_du_pdf():
    z = Z(jour=date(2026, 3, 3), ca_ttc=1000, ca_ht=900, ticket_moyen=25)
    html = rapport.construire(rapport.DonneesRapport(
        aujourdhui=date(2026, 3, 4), veille=date(2026, 3, 3), z=z, etat_z="recu",
        detail_z=z_pdf.lire_texte(TEXTE)))
    assert "Tickets : 40" in html
    assert "Livraison : 600,00 € (60 %)" in html and "A Emporter : 350,00 € (35 %)" in html
    assert "Paiements : CB 700,00 € (30) — Espèces 200,00 € (8) — Ticket restaurant 100,00 € (2)" in html
