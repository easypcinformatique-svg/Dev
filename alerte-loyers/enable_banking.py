"""Client minimal de l'API Enable Banking (lecture seule des comptes)."""
import time

import jwt
import requests

API = "https://api.enablebanking.com"


class EnableBanking:
    def __init__(self, app_id, cle_privee_pem):
        self.app_id = app_id
        self.cle_privee = cle_privee_pem

    def _entetes(self):
        maintenant = int(time.time())
        jeton = jwt.encode(
            {"iss": "enablebanking.com", "aud": "api.enablebanking.com",
             "iat": maintenant, "exp": maintenant + 3600},
            self.cle_privee,
            algorithm="RS256",
            headers={"kid": self.app_id},
        )
        return {"Authorization": f"Bearer {jeton}"}

    def _get(self, chemin, params=None):
        r = requests.get(API + chemin, headers=self._entetes(), params=params, timeout=60)
        r.raise_for_status()
        return r.json()

    def _post(self, chemin, corps):
        r = requests.post(API + chemin, headers=self._entetes(), json=corps, timeout=60)
        r.raise_for_status()
        return r.json()

    def banques(self, pays="FR"):
        return self._get("/aspsps", {"country": pays})["aspsps"]

    def demarrer_autorisation(self, banque, pays, url_retour, valide_jusqu_au, etat):
        return self._post("/auth", {
            "access": {"valid_until": valide_jusqu_au},
            "aspsp": {"name": banque, "country": pays},
            "state": etat,
            "redirect_url": url_retour,
            "psu_type": "personal",
        })["url"]

    def creer_session(self, code):
        return self._post("/sessions", {"code": code})

    def session(self, session_id):
        return self._get(f"/sessions/{session_id}")

    def transactions(self, compte_uid, date_debut, date_fin):
        """Toutes les transactions entre deux dates (AAAA-MM-JJ, incluses), toutes pages."""
        resultat, cle = [], None
        while True:
            params = {"date_from": date_debut, "date_to": date_fin}
            if cle:
                params["continuation_key"] = cle
            page = self._get(f"/accounts/{compte_uid}/transactions", params)
            resultat.extend(page.get("transactions") or [])
            cle = page.get("continuation_key")
            if not cle:
                return resultat
