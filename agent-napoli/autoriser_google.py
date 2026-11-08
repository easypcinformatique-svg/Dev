"""À lancer UNE fois, sur ton ordinateur, pour autoriser l'agent sur le compte
carpentraspizzanapoli@gmail.com.

    pip install google-auth-oauthlib
    python autoriser_google.py client_secret.json

Un navigateur s'ouvre : connecte-toi avec carpentraspizzanapoli@gmail.com et
accepte. Le script affiche les trois valeurs à coller dans les secrets GitHub.
Ne les envoie à personne et ne les mets jamais dans un fichier du dépôt.
"""

import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.events",
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    chemin = sys.argv[1]
    flow = InstalledAppFlow.from_client_secrets_file(chemin, SCOPES)
    # prompt=consent garantit qu'un jeton de rafraîchissement est bien renvoyé.
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline",
                                  login_hint="carpentraspizzanapoli@gmail.com")
    client = json.load(open(chemin))
    client = client.get("installed") or client.get("web")
    print("\nAutorisation réussie. Crée ces trois secrets dans GitHub :\n")
    print(f"GOOGLE_CLIENT_ID      = {client['client_id']}")
    print(f"GOOGLE_CLIENT_SECRET  = {client['client_secret']}")
    print(f"GOOGLE_REFRESH_TOKEN  = {creds.refresh_token}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
