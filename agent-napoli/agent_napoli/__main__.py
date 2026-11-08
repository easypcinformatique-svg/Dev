"""Passage quotidien de l'agent Pizza Napoli.

    python -m agent_napoli            # passage normal (seulement à partir de 9h, une fois par jour)
    python -m agent_napoli --essai    # lit tout, n'écrit rien, affiche le rapport
    python -m agent_napoli --forcer   # ignore l'heure et le « déjà fait aujourd'hui »
    python -m agent_napoli --z FICHIER.html "OBJET"   # lit un Z enregistré, sans Google ni IA
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from datetime import datetime, timedelta

from . import banque, caisse, comptable, config, factures, obligations, rapport, tri_mails, z_laddition
from .journal import Journal, deja_fait


def tester_z(chemin: str, objet: str) -> int:
    z = z_laddition.lire_z(open(chemin, encoding="utf-8").read(), objet)
    print(f"Z du {z.jour} : CA TTC {z.ca_ttc} — {len(z.ventes)} lignes — exports : {', '.join(z.exports)}")
    for a in z_laddition.controler(z):
        print(f"  [{a.gravite}] {a.titre} : {a.detail}")
    return 0


def passage(essai: bool, forcer: bool) -> int:
    from .google_api import Google   # import tardif : --z fonctionne sans les bibliothèques Google

    maintenant = datetime.now(config.PARIS)
    aujourdhui = maintenant.date()
    veille = aujourdhui - timedelta(days=1)
    journal = Journal()
    g = Google(essai=essai, journal=journal)

    lignes_journal = g.lignes("Journal")
    marqueur = aujourdhui.isoformat()
    if not forcer:
        if maintenant.hour < config.HEURE_RAPPORT:
            print(f"Il est {maintenant:%H:%M} à Paris : le passage se fait à partir de {config.HEURE_RAPPORT}h.")
            return 0
        if deja_fait(lignes_journal, "rapport envoyé", marqueur):
            print("Rapport du jour déjà envoyé.")
            return 0

    erreurs: list[str] = []
    g.dossier(config.SOUS_DOSSIERS[0])
    for sous in config.SOUS_DOSSIERS[1:]:
        g.dossier(sous)
    g.dossier("Factures", config.DOSSIER_A_TRAITER)
    g.dossier("Banque", config.DOSSIER_A_TRAITER)

    # Factures déjà connues (anti-doublon)
    lignes_factures = g.lignes("Factures")
    vues = factures.cles_existantes(lignes_factures)

    # 1. Tri des mails (lit aussi le Z et les factures reçues par mail)
    bilan = tri_mails.trier(g, vues, journal)
    erreurs += bilan.erreurs

    # 2. Factures déposées dans Drive « À traiter »
    bilan.factures += factures.traiter_dossier_a_traiter(g, vues)
    for r in bilan.factures:
        journal("factures", r.statut, r.detail)

    # 3. Caisse : archivage, historique, contrôles
    lignes_ventes = g.lignes("Ventes")
    lignes_produits = g.lignes("Ventes produits")
    histo = caisse.historique(lignes_ventes)
    z_veille, alertes, ca_s7, detail_veille = None, [], None, None
    for z in sorted(bilan.z, key=lambda z: z.jour):
        erreurs_z, detail = caisse.archiver(g, z)
        erreurs += [f"Z du {z.jour} : {e}" for e in erreurs_z]
        alertes_z = z_laddition.controler(z) + z_laddition.controler_tendances(
            z, histo, caisse.dernieres_ventes(lignes_produits, z.jour))
        if caisse.enregistrer(g, z, lignes_ventes, detail):
            journal("caisse", "Z enregistré", f"{z.jour} : {z.ca_ttc:.2f} € TTC")
        if z.jour == veille:
            z_veille, alertes, detail_veille = z, alertes_z, detail
            s7 = [h for h in histo if h.jour == veille - timedelta(days=7)]
            ca_s7 = s7[0].ca_ttc if s7 else None
        else:
            for a in alertes_z:
                alertes.append(z_laddition.Alerte(a.gravite, f"{a.titre} (Z du {z.jour:%d/%m})", a.detail))
    if z_veille is not None:
        etat_z = "recu"
    elif veille.weekday() in config.JOURS_FERMES:
        etat_z = "ferme"
    elif caisse.deja_enregistre(lignes_ventes, veille):
        etat_z = "deja_traite"   # Z reçu et traité lors d'un passage précédent
    else:
        etat_z = "manquant"

    # 4. Échéances : factures et obligations légales
    lignes_factures = g.lignes("Factures") if not essai else lignes_factures
    echeances = factures.echeances_a_payer(lignes_factures, aujourdhui)
    obligs, erreurs_oblig = obligations.lire(g.lignes("Obligations"), aujourdhui)
    erreurs += erreurs_oblig
    obligations.synchroniser_agenda(g, [o for o in obligs if o.jours_restants(aujourdhui) <= 60])

    # 5. Relevé de compte déposé par un gérant : rapprochement avec les factures
    lignes_banque: list[str] = []
    for b in banque.traiter_dossier(g, lignes_factures, g.lignes("Ventes") if not essai else lignes_ventes):
        erreurs += b.erreurs
        lignes_banque += b.lignes_rapport
        if b.mois:
            journal("banque", "relevé traité", b.mois)
    annee_r, mois_r = comptable.mois_precedent(aujourdhui)
    attendu = f"{annee_r}-{mois_r:02d}"
    if not deja_fait(lignes_journal + journal.lignes, "relevé traité", attendu):
        lignes_banque.append(f"En attente : le relevé de compte de {attendu[5:]}/{attendu[:4]}, à déposer dans "
                             "Drive « Pizza Napoli/Banque/À traiter » avant le dépôt Cegid.")

    # 6. Comptable, le 1er du mois : dossier à déposer sur Cegid
    message_comptable = None
    annee_c, mois_c = comptable.mois_precedent(aujourdhui)
    mois = f"{annee_c}-{mois_c:02d}"
    if aujourdhui.day == 1 and not deja_fait(lignes_journal, "dossier Cegid", mois):
        message_comptable = comptable.preparer_depot(g, lignes_factures, lignes_ventes, aujourdhui)
        journal("comptable", "dossier Cegid", mois)

    # 7. Rapport
    donnees = rapport.DonneesRapport(
        aujourdhui=aujourdhui, veille=veille,
        z=z_veille, etat_z=etat_z, detail_z=detail_veille,
        top=caisse.top_produits(z_veille) if z_veille else [],
        ca_semaine_precedente=ca_s7, alertes=alertes, factures=bilan.factures,
        echeances=echeances, obligations=[o for o in obligs if o.jours_restants(aujourdhui) <= 7],
        mails_importants=bilan.importants, nb_brouillons=g.nb_brouillons(),
        comptable=message_comptable, banque=lignes_banque, erreurs=erreurs,
        lien_classeur=g.lien_classeur(),
    )
    html = rapport.construire(donnees)
    g.envoyer(config.GERANTS, rapport.objet(donnees), html)
    journal("rapport", "rapport envoyé", marqueur)
    journal.sauver(g)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agent_napoli")
    p.add_argument("--essai", action="store_true", help="ne rien écrire, afficher le rapport")
    p.add_argument("--forcer", action="store_true", help="ignorer l'heure et le « déjà fait »")
    p.add_argument("--z", nargs=2, metavar=("FICHIER", "OBJET"), help="lire un Z enregistré")
    a = p.parse_args(argv)
    if a.z:
        return tester_z(*a.z)
    if os.getenv("GITHUB_ACTIONS") != "true":
        return passage(a.essai, a.forcer)
    # Logs publics : on montre où l'erreur s'est produite, jamais son message (qui peut
    # contenir l'objet d'un mail ou un montant).
    try:
        return passage(a.essai, a.forcer)
    except Exception as e:
        print(f"ERREUR {type(e).__name__} — détail masqué (dépôt public). Pile :", file=sys.stderr)
        for f in traceback.extract_tb(e.__traceback__):
            print(f"  {os.path.basename(f.filename)}:{f.lineno} dans {f.name}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
