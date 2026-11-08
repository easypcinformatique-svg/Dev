"""Passage complet du matin, avec faux Google, fausse IA et faux téléchargements."""

from datetime import datetime

import pytest

import agent_napoli.__main__ as principal
from agent_napoli import caisse, config, google_api, ia
from conftest import OBJET_Z, FauxGoogle, mail, piece_pdf
from test_admin import FACTURE_METRO, TRI_CLIENT


class Horloge(datetime):
    instant = datetime(2026, 10, 18, 10, 0, tzinfo=config.PARIS)

    @classmethod
    def now(cls, tz=None):
        return cls.instant


@pytest.fixture
def monde(monkeypatch, html_z):
    g = FauxGoogle([
        mail("z", "L'Addition <noreply@laddition.com>", OBJET_Z, texte="", html=html_z),
        mail("metro", "Metro <factures@metro.fr>", "Votre facture", pieces=[piece_pdf()]),
        mail("client", "Marie <marie@example.com>", "Livraison à Mazan ?"),
    ])
    g.ajouts["Obligations"] = [["TVA", "2026-10-19", "mensuelle", ""]]
    monkeypatch.setattr(google_api, "Google", lambda essai, journal: g)
    monkeypatch.setattr(principal, "datetime", Horloge)
    monkeypatch.setattr(ia, "lire_facture", lambda *a, **k: dict(FACTURE_METRO))
    monkeypatch.setattr(ia, "trier_mail", lambda e, o, c, p, l: dict(
        {"categorie": "facture", "libelle": "Factures", "important": False, "resume": "Facture Metro", "action": None,
         "brouillon_reponse": None} if "facture" in o.lower() else TRI_CLIENT))
    telechargements = []
    monkeypatch.setattr(caisse, "_telecharger", lambda url: (telechargements.append(url), (b"a;b", "text/csv", "csv"))[1])
    monkeypatch.setattr(config, "GERANTS", ["gerant1@example.com", "gerant2@example.com"])
    g.telechargements = telechargements
    return g


def test_passage_complet(monde):
    g = monde
    assert principal.main(["--forcer"]) == 0

    # Un seul rapport, aux deux gérants, avec les alertes du Z et l'échéance TVA du lendemain.
    assert len(g.envois) == 1
    a, objet, html = g.envois[0]
    assert a == ["gerant1@example.com", "gerant2@example.com"]
    assert objet.startswith("[Agent Pizza Napoli] Rapport du dimanche 18 octobre — 3 alertes")
    for attendu in ["Annulations après ticket de caisse", "Échéance légale", "TVA — demain",
                    "875,00 €", "ROMAINE (8)", "Facture <span style='color:#27ae60'>classée</span>",
                    "Livraison à Mazan", "1 brouillon(s)"]:
        assert attendu in html, attendu
    assert "Z manquant" not in html

    # Caisse : 5 exports + 30 Z archivés, chiffres inscrits.
    assert len(g.telechargements) == 35
    assert g.ajouts["Ventes"][0][:2] == ["2026-10-17", 875.0]
    # Facture rangée, agenda alimenté, journal sauvegardé.
    assert ("Factures/2026-10", "2026-10-15_Metro-Avignon_F-2026-118_435,19EUR.pdf") in g.depots
    assert g.evenements[0][2] == "2026-10-19"
    assert ["rapport", "rapport envoyé", "2026-10-18"] == g.ajouts["Journal"][-1][1:]


def test_pas_de_second_rapport_le_meme_jour(monde):
    g = monde
    principal.main([])
    principal.main([])
    assert len(g.envois) == 1


def test_rien_avant_9h(monde, monkeypatch):
    monkeypatch.setattr(Horloge, "instant", datetime(2026, 10, 18, 8, 0, tzinfo=config.PARIS))
    principal.main([])
    assert not monde.envois


def test_z_manquant_le_lendemain(monde, monkeypatch):
    g = monde
    principal.main([])
    monkeypatch.setattr(Horloge, "instant", datetime(2026, 10, 19, 9, 5, tzinfo=config.PARIS))
    principal.main([])
    assert len(g.envois) == 2 and "Z manquant" in g.envois[1][2]
    assert len(g.telechargements) == 35          # le Z du 17 n'est pas relu le 19
    assert len(g.ajouts["Factures"]) == 1


def test_jour_ferme(monde, monkeypatch):
    g = monde
    principal.main([])
    monkeypatch.setattr(Horloge, "instant", datetime(2026, 10, 19, 9, 5, tzinfo=config.PARIS))
    monkeypatch.setattr(config, "JOURS_FERMES", {6})   # dimanche 18
    principal.main([])
    assert "Z manquant" not in g.envois[1][2] and "Jour de fermeture" in g.envois[1][2]
