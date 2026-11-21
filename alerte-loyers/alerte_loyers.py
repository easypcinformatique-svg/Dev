"""Vérifie chaque mois que les loyers sont arrivés et envoie une alerte.

Lancé par GitHub Actions (.github/workflows/alerte-loyers.yml). Toute la
configuration vient de variables d'environnement (secrets GitHub) : le dépôt
étant public, aucun nom ni montant n'est écrit dans le code ni dans les logs.

Variables :
  EB_APP_ID, EB_CLE_PRIVEE   application Enable Banking
  EB_SESSIONS                identifiant(s) de session bancaire, séparés par des virgules
  BAUX_JSON                  liste des baux (voir baux.exemple.json)
  GMAIL_ADRESSE, GMAIL_MOT_DE_PASSE_APPLI, ALERTE_DESTINATAIRE (facultatif)
  NTFY_SUJET                 canal ntfy pour la notification sur le téléphone

Options :
  --seulement-si-probleme    n'envoie rien si tous les loyers sont reçus
  --mois AAAA-MM             vérifie un mois passé (par défaut : le mois en cours)
  --essai                    affiche le message au lieu de l'envoyer (usage local)
"""
import argparse
import calendar
import json
import os
import smtplib
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import requests

from enable_banking import EnableBanking
from rapprochement import MANQUANT, PARTIEL, RECU, charger_baux, rapprocher, virement_depuis_transaction

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
ICONES = {RECU: "✅", PARTIEL: "⚠️", MANQUANT: "❌"}
JOURS_AVANT_RENOUVELLEMENT = 15


def euros(montant):
    return f"{montant:,.2f} €".replace(",", " ").replace(".", ",")


def jj_mm(date_iso):
    return f"{date_iso[8:10]}/{date_iso[5:7]}" if len(date_iso) >= 10 else date_iso


def periode(mois_arg, aujourd_hui):
    if mois_arg:
        annee, mois = map(int, mois_arg.split("-"))
    else:
        annee, mois = aujourd_hui.year, aujourd_hui.month
    debut = date(annee, mois, 1)
    fin = date(annee, mois, calendar.monthrange(annee, mois)[1])
    return debut, min(fin, aujourd_hui)


def lire_virements(client, session_ids, debut, fin, aujourd_hui):
    """Renvoie (virements du mois, avertissements sur l'accès bancaire)."""
    virements, avertissements, deja_vus = [], [], set()
    for session_id in session_ids:
        session = client.session(session_id)
        banque = (session.get("aspsp") or {}).get("name", "banque")
        if session.get("status") != "AUTHORIZED":
            raise RuntimeError(f"accès à {banque} expiré ou révoqué (statut {session.get('status')})")
        limite = (session.get("access") or {}).get("valid_until")
        if limite:
            fin_acces = datetime.fromisoformat(limite.replace("Z", "+00:00")).date()
            if fin_acces - aujourd_hui <= timedelta(days=JOURS_AVANT_RENOUVELLEMENT):
                avertissements.append(
                    f"🔑 L'accès à {banque} expire le {fin_acces:%d/%m/%Y} : pense à le renouveler.")
        for compte in session.get("accounts") or []:
            uid = compte if isinstance(compte, str) else compte.get("uid")
            for tx in client.transactions(uid, debut.isoformat(), fin.isoformat()):
                cle = tx.get("entry_reference") or tx.get("transaction_id") or json.dumps(tx, sort_keys=True)
                if (uid, cle) in deja_vus:
                    continue
                deja_vus.add((uid, cle))
                virement = virement_depuis_transaction(tx)
                if virement:
                    virements.append(virement)
    return virements, avertissements


def rediger(resultats, avertissements, debut):
    problemes = [r for r in resultats if r.statut != RECU]
    nom_mois = f"{MOIS[debut.month - 1]} {debut.year}"
    if problemes:
        titre = f"⚠️ Loyers {nom_mois} : {len(problemes)} à vérifier"
    else:
        titre = f"✅ Loyers {nom_mois} : {len(resultats)}/{len(resultats)} reçus"

    lignes = []
    for r in resultats:
        detail = " + ".join(f"{euros(v.montant)} le {jj_mm(v.date)}" for v in r.virements)
        if r.statut == RECU:
            ligne = f"{ICONES[RECU]} {r.bail.nom} : {euros(r.total)} reçus ({detail})"
        elif r.statut == PARTIEL:
            ligne = (f"{ICONES[PARTIEL]} {r.bail.nom} : {euros(r.total)} reçus sur {euros(r.bail.montant)}, "
                     f"il manque {euros(r.manque)} ({detail})")
        else:
            ligne = f"{ICONES[MANQUANT]} {r.bail.nom} : rien reçu (attendu {euros(r.bail.montant)})"
        lignes.append(ligne)
    total_recu = sum((r.total for r in resultats), Decimal("0"))
    total_attendu = sum((r.bail.montant for r in resultats), Decimal("0"))
    lignes += ["", f"Total reçu : {euros(total_recu)} sur {euros(total_attendu)} attendus."]
    if avertissements:
        lignes += [""] + avertissements
    return titre, "\n".join(lignes), bool(problemes)


def envoyer_email(titre, corps):
    adresse = os.environ["GMAIL_ADRESSE"]
    message = EmailMessage()
    message["Subject"] = titre
    message["From"] = adresse
    message["To"] = os.environ.get("ALERTE_DESTINATAIRE") or adresse
    message.set_content(corps + "\n\n— Alerte loyers automatique")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as smtp:
        smtp.login(adresse, os.environ["GMAIL_MOT_DE_PASSE_APPLI"])
        smtp.send_message(message)


def envoyer_notification(titre, corps, urgent):
    r = requests.post("https://ntfy.sh/", timeout=30, json={
        "topic": os.environ["NTFY_SUJET"],
        "title": titre,
        "message": corps,
        "priority": 4 if urgent else 3,
        "tags": ["house"],
    })
    r.raise_for_status()


def envoyer(titre, corps, urgent, essai):
    if essai:
        print(titre, corps, sep="\n\n")
        return
    erreurs = []
    for canal, envoi in (("e-mail", lambda: envoyer_email(titre, corps)),
                         ("notification", lambda: envoyer_notification(titre, corps, urgent))):
        try:
            envoi()
            print(f"{canal} envoyé")
        except Exception as e:  # un canal en panne ne doit pas bloquer l'autre
            erreurs.append(f"{canal} : {type(e).__name__}")
    if erreurs:
        raise RuntimeError("échec d'envoi — " + ", ".join(erreurs))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seulement-si-probleme", action="store_true")
    parser.add_argument("--mois")
    parser.add_argument("--essai", action="store_true")
    args = parser.parse_args()

    aujourd_hui = datetime.now(ZoneInfo("Europe/Paris")).date()
    debut, fin = periode(args.mois, aujourd_hui)
    baux = charger_baux(json.loads(os.environ["BAUX_JSON"]))
    client = EnableBanking(os.environ["EB_APP_ID"], os.environ["EB_CLE_PRIVEE"])
    sessions = [s.strip() for s in os.environ["EB_SESSIONS"].split(",") if s.strip()]

    try:
        virements, avertissements = lire_virements(client, sessions, debut, fin, aujourd_hui)
    except Exception as e:
        # Un silence ne doit jamais passer pour « tout va bien » : on prévient.
        raison = str(e) if isinstance(e, RuntimeError) else type(e).__name__
        envoyer("🚨 Alerte loyers : impossible de lire tes comptes",
                f"La vérification des loyers n'a pas pu se faire ({raison}).\n"
                "Si l'accès bancaire a expiré, relance la connexion (voir alerte-loyers/README.md).",
                urgent=True, essai=args.essai)
        print("Lecture des comptes impossible :", raison)
        return 1

    resultats = rapprocher(baux, virements)
    titre, corps, probleme = rediger(resultats, avertissements, debut)
    recus = sum(r.statut == RECU for r in resultats)
    print(f"{recus}/{len(resultats)} loyers reçus")  # logs publics : pas de nom ni de montant

    if args.seulement_si_probleme and not probleme and not avertissements:
        print("Tout est reçu : pas de rappel envoyé")
        return 0
    envoyer(titre, corps, urgent=probleme, essai=args.essai)
    return 0


if __name__ == "__main__":
    sys.exit(main())
