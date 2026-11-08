from datetime import date, timedelta

import pytest

from agent_napoli import caisse, config, z_laddition
from agent_napoli.z_laddition import JourHistorique, LigneVente, Z
from conftest import OBJET_Z


def test_lecture_des_totaux(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    assert z.jour == date(2026, 10, 17)
    assert (z.ca_ttc, z.ca_ht, z.remises, z.offerts) == (875.0, 795.0, 0.0, 95.4)
    assert z.ticket_moyen == 27.34
    assert (z.corrections_avant, z.corrections_apres, z.annulations) == (128.8, 0.0, 115.9)
    assert z.tickets == 32


def test_lecture_des_ventes(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    assert len(z.ventes) == 41
    assert z.ventes[0] == LigneVente("LES CLASSIQUES", "ROMAINE", 8.0, 60.0, 54.55)
    assert sum(v.quantite for v in z.ventes) == 85
    # Le total des lignes retombe sur le CA du Z.
    assert sum(v.ttc for v in z.ventes) == pytest.approx(z.ca_ttc)


def test_lecture_des_liens(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    assert set(z.exports) == {"z-digital", "export-ventes", "export-lignes-ventes",
                              "export-reglements", "export-annulations"}
    assert z.exports["export-annulations"].endswith("/annulations")
    assert len(z.z_pdf) == 30


def test_mail_qui_n_est_pas_un_z():
    with pytest.raises(ValueError):
        z_laddition.lire_z("<p>Bonjour</p>", OBJET_Z)
    with pytest.raises(ValueError):
        z_laddition.lire_z("<p>CA TTC : 10</p>", "Objet sans date")


def test_controles_du_17_octobre(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    titres = {a.titre: a for a in z_laddition.controler(z)}
    assert "13,2 %" in titres["Annulations après ticket de caisse"].detail
    assert titres["Offerts élevés"].gravite == "haute"
    assert "Boissons de l'offre flyer ce jour : 8" in titres["Offerts élevés"].detail
    assert "Corrections élevées" in titres


def test_offerts_hors_boissons(html_z, monkeypatch):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    assert z_laddition.valeur_boissons_offertes(z) == (8, 24.0)
    monkeypatch.setattr(config, "OFFERTS_INCLUENT_BOISSONS", True)
    alerte = [a for a in z_laddition.controler(z) if a.titre == "Offerts élevés"][0]
    assert alerte.detail.startswith("71,40 €")


def test_journee_propre_sans_alerte():
    z = Z(jour=date(2026, 10, 18), ca_ttc=1000, ticket_moyen=25, offerts=20, annulations=10)
    assert z_laddition.controler(z) == []


def _histo(fin, n, ca=1000.0, ticket=25.0):
    return [JourHistorique(fin - timedelta(days=i), ca, ticket) for i in range(1, n + 1)]


def test_baisse_de_ca_et_de_ticket_moyen():
    jour = date(2026, 10, 24)
    z = Z(jour=jour, ca_ttc=700, ticket_moyen=20)
    titres = {a.titre for a in z_laddition.controler_tendances(z, _histo(jour, 20), {})}
    assert {"CA en baisse", "Ticket moyen en baisse"} <= titres


def test_record_du_mois():
    jour = date(2026, 10, 24)
    z = Z(jour=jour, ca_ttc=1500, ticket_moyen=25)
    titres = {a.titre for a in z_laddition.controler_tendances(z, _histo(jour, 20), {})}
    assert titres == {"Record du mois"}


def test_pizza_qui_ne_se_vend_plus():
    jour = date(2026, 10, 24)
    z = Z(jour=jour, ca_ttc=1000, ticket_moyen=25, ventes=[LigneVente("LES CLASSIQUES", "REINE", 3, 30, 27)])
    dernieres = {"CATALANE": ("LES MARITIMES", jour - timedelta(days=15)),
                 "REINE": ("LES CLASSIQUES", jour - timedelta(days=20)),
                 "FANTA 1,5L": ("BOISSONS", jour - timedelta(days=30)),
                 "SAUMON": ("LES BLANCHES", jour - timedelta(days=3))}
    alertes = z_laddition.controler_tendances(z, _histo(jour, 20), dernieres)
    oubli = [a for a in alertes if a.titre == "Pizzas qui ne se vendent plus"]
    assert oubli and oubli[0].detail.endswith(": CATALANE.")


def test_pas_d_alerte_pizza_sans_assez_d_historique():
    jour = date(2026, 10, 24)
    z = Z(jour=jour, ca_ttc=1000, ticket_moyen=25)
    dernieres = {"CATALANE": ("LES MARITIMES", jour - timedelta(days=40))}
    assert not z_laddition.controler_tendances(z, _histo(jour, 5), dernieres)


def test_enregistrement_une_seule_fois(html_z):
    from conftest import FauxGoogle
    g = FauxGoogle()
    z = z_laddition.lire_z(html_z, OBJET_Z)
    lignes = []
    assert caisse.enregistrer(g, z, lignes) is True
    assert caisse.enregistrer(g, z, lignes) is False
    assert len(g.ajouts["Ventes"]) == 1 and len(g.ajouts["Ventes produits"]) == 41


def test_historique_et_top(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    assert caisse.top_produits(z, 3) == [("ROMAINE", 8.0), ("KEBAB", 5.0), ("4 FRO", 4.0)]
    histo = caisse.historique([["2026-10-16", "1 234,50", "1100", "26,1"], ["en-tête"], ["2026-10-15", "x"]])
    assert histo == [JourHistorique(date(2026, 10, 16), 1234.5, 26.1)]
    produits = [["2026-10-01", "LES MARITIMES", "CATALANE", "2"], ["2026-10-05", "LES MARITIMES", "CATALANE", "1"],
                ["2026-10-17", "LES MARITIMES", "CATALANE", "1"], ["2026-10-06", "BOISSONS", "COCA", "0"]]
    assert caisse.dernieres_ventes(produits, date(2026, 10, 17)) == {"CATALANE": ("LES MARITIMES", date(2026, 10, 5))}


def test_mail_mis_en_page_avec_tableaux_imbriques(html_z):
    """Les vrais mails enveloppent souvent tout le contenu dans des tableaux de mise en page."""
    corps = html_z.split("<body>", 1)[1].split("</body>", 1)[0]
    enveloppe = (f"<html><body><table width='100%'><tr><td></td><td>{corps}</td><td>1</td><td>2</td><td>3</td></tr>"
                 "</table></body></html>")
    z = z_laddition.lire_z(enveloppe, OBJET_Z)
    assert len(z.ventes) == 41 and z.ca_ttc == 875.0


def test_version_texte_du_vrai_mail():
    """Texte du Z du 17/10/2026 tel qu'affiché par Gmail (copié depuis la boîte de la pizzeria)."""
    from conftest import FIXTURES
    texte = (FIXTURES / "z_2026-10-17_texte.txt").read_text(encoding="utf-8")
    z = z_laddition.lire_z(texte, OBJET_Z)
    assert (z.ca_ttc, z.offerts, z.annulations, z.ticket_moyen) == (875.0, 95.4, 115.9, 27.34)
    assert len(z.ventes) == 41
    assert z.ventes[-1] == LigneVente("BOISSONS", "FANTA 1,5L", 1.0, 3.0, 2.84)
    assert z.ventes[38] == LigneVente("VIN", "Petite balade rosé", 1.0, 6.0, 5.0)
    assert sum(v.ttc for v in z.ventes) == pytest.approx(875.0)
    assert len(z_laddition.controler(z)) == 3
