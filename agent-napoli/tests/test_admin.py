"""Factures, obligations, tri des mails, comptable et rapport, avec un faux Google et une fausse IA."""

from datetime import date

import pytest

from agent_napoli import comptable, config, factures, ia, obligations, rapport, tri_mails, z_laddition
from agent_napoli.google_api import PieceJointe
from conftest import OBJET_Z, FauxGoogle, mail, piece_pdf

FACTURE_METRO = {"est_une_facture": True, "fournisseur": "Metro Avignon", "numero": "F-2026/118",
                 "date_facture": "2026-10-15", "date_echeance": "2026-11-14", "montant_ht": 412.5,
                 "montant_tva": 22.69, "montant_ttc": 435.19, "deja_payee": False,
                 "categorie": "matieres premieres"}


@pytest.fixture
def ia_factice(monkeypatch):
    appels = {"factures": [], "tri": []}
    reponses = {"facture": dict(FACTURE_METRO), "tri": None}

    def lire_facture(donnees, mime, contexte=""):
        appels["factures"].append(mime)
        r = reponses["facture"]
        if isinstance(r, Exception):
            raise r
        return dict(r)

    def trier_mail(expediteur, objet, corps, pieces, libelles):
        appels["tri"].append(objet)
        appels.setdefault("libelles", libelles)
        return dict(reponses["tri"])

    monkeypatch.setattr(ia, "lire_facture", lire_facture)
    monkeypatch.setattr(ia, "trier_mail", trier_mail)
    return appels, reponses


# ------------------------------------------------------------------ factures
def test_nom_de_fichier():
    assert factures.nom_fichier(FACTURE_METRO, "application/pdf") == \
        "2026-10-15_Metro-Avignon_F-2026-118_435,19EUR.pdf"
    assert factures.nom_fichier({"fournisseur": "Boulangerie Élise", "date_facture": "2026-10-01"},
                                "image/jpeg") == "2026-10-01_Boulangerie-Elise.jpg"


def test_facture_classee_puis_doublon(ia_factice):
    g = FauxGoogle()
    vues = set()
    r = factures.traiter_document(g, b"%PDF", "application/pdf", "mail", vues)
    assert r.statut == "classée" and r.detail == "Metro Avignon : 435.19 €"
    assert g.depots == [("Factures/2026-10", "2026-10-15_Metro-Avignon_F-2026-118_435,19EUR.pdf")]
    ligne = g.ajouts["Factures"][0]
    assert ligne[1:9] == ["Metro Avignon", "F-2026/118", "2026-10-15", "2026-11-14", 412.5, 22.69, 435.19, "à payer"]

    r2 = factures.traiter_document(g, b"%PDF", "application/pdf", "mail", vues)
    assert r2.statut == "doublon" and len(g.ajouts["Factures"]) == 1
    # Doublon aussi reconnu depuis le tableur, au passage suivant.
    assert factures.cles_existantes(g.ajouts["Factures"]) == vues


def test_document_qui_n_est_pas_une_facture(ia_factice):
    _, reponses = ia_factice
    reponses["facture"] = {**FACTURE_METRO, "est_une_facture": False}
    g = FauxGoogle()
    assert factures.traiter_document(g, b"x", "image/jpeg", "mail", set()).statut == "pas une facture"
    assert not g.depots and "Factures" not in g.ajouts


def test_erreur_ia_n_ecrit_rien(ia_factice):
    _, reponses = ia_factice
    reponses["facture"] = ia.ErreurIA("limite de débit atteinte")
    g = FauxGoogle()
    assert factures.traiter_document(g, b"x", "application/pdf", "mail", set()).statut == "erreur"
    assert not g.depots


def test_dossier_a_traiter_deplace_le_fichier(ia_factice):
    g = FauxGoogle(fichiers_a_traiter=[
        {"id": "f1", "name": "scan.jpg", "mimeType": "image/jpeg"},
        {"id": "f2", "name": "notes.docx", "mimeType": "application/msword"}])
    res = factures.traiter_dossier_a_traiter(g, set())
    assert [r.statut for r in res] == ["erreur", "classée"] or [r.statut for r in res] == ["classée", "erreur"]
    assert g.deplacements == [("f1", "Factures/2026-10", "2026-10-15_Metro-Avignon_F-2026-118_435,19EUR.jpg")]
    assert not g.depots


def test_echeances_a_payer():
    def l(fourn, ech, statut, ttc="100"):
        return ["2026-10-01", fourn, "1", "2026-10-01", ech, "", "", ttc, statut, "", "lien", ""]
    lignes = [l("A", "2026-11-10", "à payer"), l("B", "2026-11-20", "à payer"),
              l("C", "2026-11-09", "payée"), l("D", "2026-11-01", "à payer"), l("E", "", "à payer")]
    res = factures.echeances_a_payer(lignes, date(2026, 11, 8))
    assert [(e.fournisseur, e.jours_restants(date(2026, 11, 8))) for e in res] == [("D", -7), ("A", 2)]


# --------------------------------------------------------------- obligations
def test_prochaine_occurrence():
    assert obligations.prochaine(date(2026, 1, 31), "mensuelle", date(2026, 2, 10)) == date(2026, 2, 28)
    assert obligations.prochaine(date(2026, 1, 31), "mensuelle", date(2026, 3, 1)) == date(2026, 3, 31)
    assert obligations.prochaine(date(2026, 1, 15), "trimestrielle", date(2026, 11, 8)) == date(2027, 1, 15)
    assert obligations.prochaine(date(2026, 5, 1), "annuelle", date(2026, 11, 8)) == date(2027, 5, 1)
    assert obligations.prochaine(date(2026, 5, 1), "unique", date(2026, 11, 8)) is None
    assert obligations.prochaine(date(2026, 12, 1), "", date(2026, 11, 8)) == date(2026, 12, 1)


def test_obligations_et_agenda():
    lignes = [["TVA", "2026-10-19", "mensuelle", "CA3 sur impots.gouv"], ["Assurance", "pas une date"],
              [""], ["Contrôle HACCP", "2026-11-09", "unique", "", "https://calendar/ancien"]]
    obligs, erreurs = obligations.lire(lignes, date(2026, 11, 8))
    assert [(o.libelle, o.jour) for o in obligs] == [("Contrôle HACCP", date(2026, 11, 9)), ("TVA", date(2026, 11, 19))]
    assert len(erreurs) == 1 and "Assurance" in erreurs[0]
    g = FauxGoogle()
    obligations.synchroniser_agenda(g, obligs)
    assert g.evenements[1] == ("TVA|2026-11-19", "Échéance : TVA", "2026-11-19", (7, 1))
    assert ("Obligations", 0, 4, "https://calendar/2") in g.cellules


# -------------------------------------------------------------------- tri
TRI_CLIENT = {"categorie": "client", "libelle": "NOUVELLE COMMANDE", "important": True, "resume": "Un client demande si vous livrez à Mazan.",
              "action": "Confirmer la zone de livraison", "brouillon_reponse": "Bonjour ! Oui, on livre à Mazan…"}


def test_tri_complet(ia_factice, html_z):
    appels, reponses = ia_factice
    reponses["tri"] = TRI_CLIENT
    messages = [
        mail("z", "L'Addition <noreply@laddition.com>", OBJET_Z, texte="", html=html_z),
        mail("photo", "Gérant <gerant@example.com>", "FACTURE boulangerie", pieces=[
            PieceJointe("IMG_1.jpg", "image/jpeg", donnees=b"jpeg")]),
        mail("client", "Marie <marie@example.com>", "Livraison à Mazan ?"),
        mail("deja", "x@example.com", "Ancien"),
        mail("rapport", config.BOITE_PIZZERIA, tri_mails.PREFIXE_RAPPORT + " Rapport du lundi"),
    ]
    g = FauxGoogle(messages, etiquettes={"deja": {"INBOX", "id:" + config.LIBELLE_TRAITE}})
    bilan = tri_mails.trier(g, set(), lambda *a: None)

    assert len(bilan.z) == 1 and bilan.z[0].ca_ttc == 875.0
    assert [r.statut for r in bilan.factures] == ["classée"]
    assert appels["tri"] == ["Livraison à Mazan ?"]          # ni le Z, ni la photo, ni le rapport ne passent par l'IA
    assert g.brouillons[0]["a"] == ["marie@example.com"] and g.brouillons[0]["fil"] == "fil-client"
    assert g.brouillons[0]["objet"] == "Re: Livraison à Mazan ?"
    assert bilan.importants[0].brouillon is True
    assert "deja" not in g.etiquetes
    # Uniquement les libellés existants des gérants, plus « Agent/Traité ».
    assert appels["libelles"] == FauxGoogle.LIBELLES
    assert g.etiquetes["z"] == ["Ticket Z", config.LIBELLE_TRAITE]
    assert g.etiquetes["photo"] == ["Factures", config.LIBELLE_TRAITE]
    assert g.etiquetes["client"] == ["NOUVELLE COMMANDE", config.LIBELLE_TRAITE]
    assert g.etiquetes["rapport"] == [config.LIBELLE_TRAITE]
    assert bilan.par_categorie == {"z_caisse": 1, "facture": 1, "client": 1}


def test_pas_de_brouillon_pour_un_noreply(ia_factice):
    _, reponses = ia_factice
    reponses["tri"] = {**TRI_CLIENT, "categorie": "administratif"}
    g = FauxGoogle([mail("u", "URSSAF <no-reply@urssaf.fr>", "Votre échéance")])
    bilan = tri_mails.trier(g, set(), lambda *a: None)
    assert not g.brouillons and bilan.importants and not bilan.importants[0].brouillon


def test_libelle_inconnu_ou_aucun_n_est_jamais_cree(ia_factice):
    _, reponses = ia_factice
    g = FauxGoogle([mail("a", objet="Pub"), mail("b", objet="Autre")])
    reponses["tri"] = {**TRI_CLIENT, "categorie": "publicite", "libelle": "Libellé inventé", "brouillon_reponse": None}
    tri_mails.trier(g, set(), lambda *a: None)
    assert g.etiquetes["a"] == [config.LIBELLE_TRAITE]


def test_erreur_ia_laisse_le_mail_pour_demain(monkeypatch):
    def echec(*a):
        raise ia.ErreurIA("connexion à l'API impossible")
    monkeypatch.setattr(ia, "trier_mail", echec)
    g = FauxGoogle([mail("m")])
    bilan = tri_mails.trier(g, set(), lambda *a: None)
    assert "m" not in g.etiquetes and "nouvel essai demain" in bilan.erreurs[0]


# -------------------------------------------------------------- comptable
def test_dossier_cegid():
    assert comptable.mois_precedent(date(2027, 1, 1)) == (2026, 12)
    lignes = [["2026-10-02", "Metro", "1", "2026-10-01", "", "10", "1", "11,50", "à payer", "", "https://drive.google.com/file/d/AAA/view", ""],
              ["2026-10-03", "Boulangerie", "2", "05/10/2026", "", "", "", "4", "payée", "", "", ""],
              ["2026-11-02", "Metro", "3", "2026-11-01", "", "10", "1", "11", "à payer", "", "https://drive.google.com/file/d/BBB/view", ""]]
    g = FauxGoogle()
    phrase = comptable.preparer_depot(g, lignes, [["2026-10-17", "875"], ["17/10/2026", "1"], ["2026-11-01", "900"]],
                                      date(2026, 11, 1))
    dossier = "Comptable/2026-10 à déposer sur Cegid"
    assert g.copies == [("AAA", dossier)]
    assert [d[1] for d in g.depots] == ["factures_2026-10.csv", "ventes_2026-10.csv"]
    assert "Dossier Cegid de octobre 2026" in phrase and "1 facture(s), total TTC 15,50 €" in phrase
    assert "Fichier introuvable pour : Boulangerie" in phrase
    assert not g.brouillons and not g.envois     # rien n'est envoyé au comptable


# ---------------------------------------------------------------- rapport
def test_rapport_avec_z(html_z):
    z = z_laddition.lire_z(html_z, OBJET_Z)
    d = rapport.DonneesRapport(
        aujourdhui=date(2026, 10, 18), veille=date(2026, 10, 17), z=z, etat_z="recu",
        top=[("ROMAINE", 8.0)], ca_semaine_precedente=1000.0, alertes=z_laddition.controler(z),
        echeances=[factures.Echeance("Metro", "435,19", date(2026, 10, 19), "")],
        nb_brouillons=2)
    html = rapport.construire(d)
    assert rapport.objet(d) == f"{tri_mails.PREFIXE_RAPPORT} Rapport du dimanche 18 octobre — 3 alertes"
    for attendu in ["Annulations après ticket de caisse", "875,00 €", "-12 % par rapport à samedi dernier",
                    "ROMAINE (8)", "Facture à payer", "Metro — 435,19 € — demain", "2 brouillon(s)"]:
        assert attendu in html, attendu


def test_rapport_z_manquant_ou_ferme():
    base = dict(aujourdhui=date(2026, 10, 20), veille=date(2026, 10, 19))
    manquant = rapport.construire(rapport.DonneesRapport(**base, etat_z="manquant"))
    assert "Z manquant" in manquant
    ferme = rapport.construire(rapport.DonneesRapport(**base, etat_z="ferme"))
    assert "Z manquant" not in ferme and "Jour de fermeture" in ferme


def test_rapport_echappe_le_contenu_des_mails():
    d = rapport.DonneesRapport(aujourdhui=date(2026, 10, 20), veille=date(2026, 10, 19), etat_z="ferme",
                               mails_importants=[tri_mails.MailImportant("<script>", "<b>x</b>", "r", None, False)])
    assert "<script>" not in rapport.construire(d)


def test_dates_et_nombres_du_tableur():
    from agent_napoli.outils import lire_date, lire_nombre
    assert lire_date("2026-10-17") == lire_date("17/10/2026") == lire_date("17/10/26") == date(2026, 10, 17)
    assert lire_date("31/02/2026") is None and lire_date("") is None and lire_date("demain") is None
    assert lire_nombre("1 234,50 €") == 1234.5 and lire_nombre("1.234,50") == 1234.5
    assert lire_nombre("435.19") == 435.19 and lire_nombre("") is None


def test_obligation_saisie_a_la_francaise():
    obligs, erreurs = obligations.lire([["URSSAF", "05/12/2026", "mensuelle"]], date(2026, 11, 8))
    assert not erreurs and obligs[0].jour == date(2026, 12, 5)
