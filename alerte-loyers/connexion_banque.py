"""Relie un compte bancaire à l'alerte loyers (à refaire tous les ~180 jours).

À lancer sur ton ordinateur, jamais dans GitHub Actions : il affiche
l'identifiant de session, qui ne doit pas apparaître dans des logs publics.

  1. python connexion_banque.py banques --cherche mutuel
  2. python connexion_banque.py debut --banque "<nom exact>"
       -> ouvre le lien, connecte-toi à ta banque, puis copie l'adresse
          de la page sur laquelle tu arrives à la fin
  3. python connexion_banque.py fin "<adresse copiée>"
       -> donne l'identifiant de session à mettre dans le secret EB_SESSIONS

L'application Enable Banking se lit dans EB_APP_ID et dans EB_CLE_PRIVEE
(contenu du fichier .pem), ou dans le fichier indiqué par --cle.
"""
import argparse
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from enable_banking import EnableBanking


def client(args):
    cle = open(args.cle).read() if args.cle else os.environ["EB_CLE_PRIVEE"]
    return EnableBanking(os.environ["EB_APP_ID"], cle)


def banques(args):
    for b in client(args).banques(args.pays):
        if args.cherche.lower() in b["name"].lower():
            print(b["name"])


def debut(args):
    valide = datetime.now(timezone.utc) + timedelta(days=args.jours)
    url = client(args).demarrer_autorisation(
        args.banque, args.pays, args.url_retour, valide.isoformat(timespec="seconds"), str(uuid.uuid4()))
    print("Ouvre ce lien et connecte-toi à ta banque :\n")
    print(url)


def fin(args):
    code = parse_qs(urlparse(args.retour).query).get("code", [args.retour])[0]
    session = client(args).creer_session(code)
    print("Session créée. Valable jusqu'au :", (session.get("access") or {}).get("valid_until"))
    print("Comptes accessibles :")
    for compte in session.get("accounts") or []:
        print(" -", compte.get("name") or compte.get("product") or compte.get("uid"))
    print("\nÀ copier dans le secret GitHub EB_SESSIONS :\n")
    print(session["session_id"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cle", help="fichier .pem de l'application Enable Banking")
    parser.add_argument("--pays", default="FR")
    etapes = parser.add_subparsers(dest="etape", required=True)

    p = etapes.add_parser("banques", help="cherche le nom exact d'une banque")
    p.add_argument("--cherche", default="")
    p.set_defaults(action=banques)

    p = etapes.add_parser("debut", help="crée le lien de connexion à la banque")
    p.add_argument("--banque", required=True)
    p.add_argument("--jours", type=int, default=180, help="durée de l'accès demandé")
    p.add_argument("--url-retour", default="https://enablebanking.com/",
                   help="doit être autorisée dans le panneau Enable Banking")
    p.set_defaults(action=debut)

    p = etapes.add_parser("fin", help="crée la session à partir de l'adresse de retour")
    p.add_argument("retour", help="adresse complète de la page de retour, ou juste le code")
    p.set_defaults(action=fin)

    args = parser.parse_args()
    args.action(args)


if __name__ == "__main__":
    main()
