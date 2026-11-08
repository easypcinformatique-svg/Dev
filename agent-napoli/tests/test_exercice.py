"""Suivi du CA sur l'exercice 1er juillet - 30 juin. Chiffres fictifs."""

from datetime import date, timedelta

import pytest

from agent_napoli import caisse, config, exercice, ia, liasses, rapport
from agent_napoli.exercice import Exercice, Jour
from conftest import OBJET_Z, FauxGoogle, mail


def test_dates_d_exercice():
    assert exercice.debut_exercice(date(2026, 11, 8)) == date(2026, 7, 1)
    assert exercice.debut_exercice(date(2027, 3, 1)) == date(2026, 7, 1)
    assert exercice.debut_exercice(date(2026, 6, 30)) == date(2025, 7, 1)
    assert exercice.fin_exercice(date(2026, 11, 8)) == date(2027, 6, 30)
    assert exercice.nom_exercice(date(2026, 11, 8)) == "2026-2027"
    assert exercice.un_an_avant(date(2028, 2, 29)) == date(2027, 2, 28)


def ventes_fictives(debut, fin, ca_par_jour):
    res, d = {}, debut
    while d <= fin:
        res[d] = Jour(d, ca_par_jour, 25.0, ca_par_jour * 0.6, ca_par_jour * 0.4)
        d += timedelta(days=1)
    return res


def test_suivi_avec_historique_et_liasse():
    # Exercice précédent : 500 €/jour ; exercice en cours : 550 €/jour (+10 %).
    ventes = ventes_fictives(date(2025, 7, 1), date(2026, 6, 30), 500.0)
    ventes.update(ventes_fictives(date(2026, 7, 1), date(2026, 11, 7), 550.0))
    exercices = [Exercice("2025-2026", date(2025, 7, 1), date(2026, 6, 30), 180_000.0, 10_000.0, None, "liasse")]
    s = exercice.suivre(date(2026, 11, 7), ventes, exercices)
    assert s.exercice == "2026-2027" and s.depuis == date(2026, 7, 1)
    assert s.cumul == pytest.approx(130 * 550.0) and s.cumul_n1 == pytest.approx(130 * 500.0)
    assert s.evolution == pytest.approx(0.10)
    assert s.projection_methode == "saisonnière"
    assert s.projection == pytest.approx(198_000.0)          # liasse N-1 × 1,10
    assert s.objectif == pytest.approx(198_000.0)            # +10 % par défaut
    assert s.ecart_objectif == pytest.approx(0.0, abs=0.01)


def test_objectif_saisi_et_projection_lineaire_sans_historique():
    ventes = ventes_fictives(date(2026, 7, 1), date(2026, 7, 31), 600.0)
    exercices = [Exercice("2026-2027", date(2026, 7, 1), date(2027, 6, 30), None, None, 250_000.0, "saisie")]
    s = exercice.suivre(date(2026, 7, 31), ventes, exercices)
    assert s.cumul_n1 is None and s.projection_methode == "linéaire"
    assert s.projection == pytest.approx(600.0 * 365)
    assert s.objectif == 250_000.0 and s.ecart_objectif == pytest.approx(600.0 * 365 - 250_000.0)


def test_pas_de_suivi_sans_vente():
    assert exercice.suivre(date(2026, 11, 7), {}, []) is None


def test_bilan_mensuel():
    ventes = ventes_fictives(date(2025, 10, 1), date(2025, 10, 31), 400.0)
    ventes.update(ventes_fictives(date(2026, 10, 1), date(2026, 10, 31), 500.0))
    b = exercice.bilan_mois(2026, 10, ventes)
    assert b.nom == "octobre 2026" and b.ca_ht == pytest.approx(15_500.0) and b.ca_ht_n1 == pytest.approx(12_400.0)
    assert b.part_livraison == pytest.approx(0.6) and b.ticket_moyen == 25.0


def test_lecture_des_onglets():
    col = config.ONGLETS["Ventes"]
    ligne = [""] * len(col)
    ligne[col.index("Date")], ligne[col.index("CA HT")], ligne[col.index("Ticket moyen")] = "17/10/2026", "1 000,50", "25"
    ligne[col.index("Livraison")] = "600"
    assert exercice.lire_ventes([ligne])[date(2026, 10, 17)] == Jour(date(2026, 10, 17), 1000.5, 25.0, 600.0, None)
    ex = exercice.lire_exercices([["2025-2026", "01/07/2025", "30/06/2026", "180 000", "", "", "x.pdf"], ["", "", "", "", "", "", "y.pdf"]])
    assert len(ex) == 1 and ex[0].ca_ht == 180_000.0 and ex[0].fin == date(2026, 6, 30)


def test_rapport_avec_suivi_et_bilan():
    s = exercice.Suivi("2026-2027", date(2026, 7, 1), date(2026, 11, 7), 71_500.0, 65_000.0, 180_000.0,
                       190_000.0, "saisonnière", 198_000.0)
    b = exercice.BilanMois("octobre 2026", 15_500.0, 12_400.0, 31, 25.0, 0.6)
    html = rapport.construire(rapport.DonneesRapport(aujourdhui=date(2026, 11, 1), veille=date(2026, 10, 31),
                                                     etat_z="ferme", suivi_ca=s, bilan_mois=b))
    for attendu in ["Chiffre d&#x27;affaires de l&#x27;exercice 2026-2027", "71 500,00 €", "65 000,00 € (+10,0 %)",
                    "Projection au 30/06/2027 : 190 000,00 €", "retard de 8 000,00 €", "Bilan de octobre 2026",
                    "contre 12 400,00 € un an plus tôt (+25,0 %)", "Livraison : 60 % du CA"]:
        assert attendu in html, attendu


def test_liasse_lue_une_seule_fois(monkeypatch):
    appels = []
    def lire_liasse(donnees):
        appels.append(1)
        return {"est_une_liasse": True, "exercices": [
            {"debut": "2025-07-01", "fin": "2026-06-30", "chiffre_affaires_net_ht": 180000.0, "resultat": 10000.0},
            {"debut": "2024-07-01", "fin": "2025-06-30", "chiffre_affaires_net_ht": 170000.0, "resultat": 900.0}]}
    monkeypatch.setattr(ia, "lire_liasse", lire_liasse)
    g = FauxGoogle(fichiers_a_traiter=[{"id": "L1", "name": "Liasse 2026 VF.pdf", "mimeType": "application/pdf"},
                                       {"id": "L2", "name": "Liasse 2026 provisoire.pdf", "mimeType": "application/pdf"}])
    lignes = []
    phrases, erreurs = liasses.traiter(g, lignes)
    assert not erreurs and len(appels) == 2
    assert [l[0] for l in g.ajouts["Exercices"]] == ["2025-2026", "2024-2025", ""]   # la 2e n'apporte rien de neuf
    assert "2025-2026, 2024-2025" in phrases[0]
    liasses.traiter(g, g.lignes("Exercices"))
    assert len(appels) == 2                                                          # rien n'est relu


def test_rattrapage_de_l_historique(monkeypatch, html_z):
    autre = html_z.replace("CA TTC : 875.00", "CA TTC : 500.00")
    g = FauxGoogle([mail("a", "noreply@laddition.com", OBJET_Z, texte="", html=html_z),
                    mail("b", "noreply@laddition.com", OBJET_Z.replace("2026-10-17", "2026-10-16"), texte="", html=autre),
                    mail("c", "noreply@laddition.com", OBJET_Z.replace("2026-10-17", "2026-10-15"), texte="", html=html_z),
                    mail("x", "noreply@laddition.com", "L'Addition - Votre Z quotidien (sans date)", html="")])
    g.ajouts["Ventes"] = [["2026-10-15", 1.0]]                    # déjà connu : ignoré
    monkeypatch.setattr(caisse, "_telecharger", lambda url: (_ for _ in ()).throw(OSError("expiré")))
    n = caisse.rattraper_historique(g, lambda *a: None)
    assert n == 2
    assert [l[0] for l in g.ajouts["Ventes"]] == ["2026-10-15", "2026-10-16", "2026-10-17"]
    assert g.ajouts["Ventes"][1][1] == 500.0
    assert len(g.ajouts["Ventes produits"]) == 82
