"""Module d'authentification Google OAuth2.

Gère la connexion OAuth2 pour accéder à Gmail et Google Drive.
"""

import json
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

# Scopes nécessaires pour Gmail et Drive
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

TOKEN_FILE = "token.json"


def get_flow(client_id: str, client_secret: str, redirect_uri: str) -> Flow:
    """Crée un flow OAuth2 pour l'authentification Google.

    Args:
        client_id: ID client Google OAuth
        client_secret: Secret client Google OAuth
        redirect_uri: URI de redirection

    Returns:
        Flow OAuth2
    """
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }

    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    return flow


def save_credentials(credentials: Credentials):
    """Sauvegarde les credentials dans un fichier.

    Args:
        credentials: Credentials Google OAuth
    """
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes or []),
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def load_credentials() -> Credentials | None:
    """Charge les credentials depuis le fichier.

    Returns:
        Credentials ou None si non trouvé
    """
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )

    return creds


def is_authenticated() -> bool:
    """Vérifie si l'utilisateur est authentifié."""
    creds = load_credentials()
    return creds is not None and creds.valid
