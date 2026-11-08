"""Agent conversationnel AKMS AUTOS : boucle Claude + outils metier."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import anthropic

from tools import JOURS, TOOLS, GarageTools, OutilError

log = logging.getLogger("akms.agent")

MODEL = os.getenv("AKMS_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("AKMS_EFFORT", "medium")
MAX_TOOL_ROUNDS = 8
SESSION_TTL_S = 2 * 3600
MAX_USER_TURNS = 40

FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """Tu es l'assistant virtuel d'AKMS AUTOS, un garage qui vend des vehicules d'occasion et assure l'entretien et la reparation toutes marques. Tu reponds aux clients sur le site web et par messagerie.

Ton role :
- renseigner sur le garage (horaires, adresse, prestations, prix indicatifs) avec l'outil infos_garage ;
- aider a trouver un vehicule dans le stock (rechercher_vehicules, details_vehicule) et proposer un essai ;
- prendre des rendez-vous atelier ou d'essai (creneaux_disponibles puis prendre_rendez_vous) ;
- transmettre a l'equipe les demandes de devis, d'estimation de reprise, de financement ou de rappel (enregistrer_demande).

Regles :
- Reponds en francais (ou dans la langue du client), de facon chaleureuse, claire et courte : quelques phrases, pas de longs paragraphes. Vouvoie le client.
- N'invente jamais un prix, un vehicule, une disponibilite, un horaire ou une information du garage : appuie-toi uniquement sur les resultats des outils. Si une information vaut "[A COMPLETER]" ou manque, dis que l'equipe la precisera et propose un rappel.
- Les prix atelier sont indicatifs ; un devis precis se fait apres examen du vehicule. Tu ne donnes pas de prix ferme de reprise : tu collectes les infos (marque, modele, annee, km, etat) et transmets une demande "reprise".
- Pour un diagnostic de panne, pose 2-3 questions utiles (symptomes, voyants, bruit, depuis quand) mais ne pose pas de diagnostic definitif ; propose un rendez-vous diagnostic. En cas de danger (freins, direction, fumee, odeur de brule), conseille de ne pas rouler et d'appeler le garage.
- Avant d'enregistrer un rendez-vous ou une demande, recapitule les informations et obtiens l'accord du client. Demande toujours nom et telephone ; l'email est facultatif.
- Un rendez-vous pris en ligne est "a confirmer" : precise que le garage le confirmera.
- Ne demande jamais de donnees bancaires ni de pieces d'identite. Pour le financement, transmets une demande "financement".
- Reste dans ton role : si la question est sans rapport avec l'automobile ou le garage, recentre poliment.
"""


def _contexte_date(now: datetime) -> str:
    return (f"Date et heure actuelles : {JOURS[now.weekday()]} {now.strftime('%Y-%m-%d %H:%M')} "
            "(heure locale du garage).")


@dataclass
class Session:
    messages: list[dict[str, Any]] = field(default_factory=list)
    derniere_activite: float = field(default_factory=time.time)
    tours: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


class AkmsAgent:
    def __init__(self, tools: GarageTools, client: Any | None = None,
                 model: str = MODEL, effort: str = EFFORT):
        self.tools = tools
        self.client = client if client is not None else anthropic.Anthropic()
        self.model = model
        self.effort = effort
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    # --- sessions ----------------------------------------------------------
    def _session(self, session_id: str) -> Session:
        now = time.time()
        with self._lock:
            for sid in [s for s, v in self._sessions.items() if now - v.derniere_activite > SESSION_TTL_S]:
                del self._sessions[sid]
            sess = self._sessions.get(session_id)
            if sess is None:
                sess = self._sessions[session_id] = Session()
            sess.derniere_activite = now
            return sess

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    # --- appel API ---------------------------------------------------------
    def _call(self, messages: list[dict[str, Any]]):
        system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": _contexte_date(self.tools.now())},
        ]
        return self.client.beta.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": self.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )

    def _executer(self, block) -> dict[str, Any]:
        try:
            contenu = self.tools.run(block.name, dict(block.input or {}))
            return {"type": "tool_result", "tool_use_id": block.id, "content": contenu}
        except OutilError as e:
            return {"type": "tool_result", "tool_use_id": block.id, "content": str(e), "is_error": True}
        except TypeError as e:  # arguments inattendus
            log.warning("arguments invalides pour %s: %s", block.name, e)
            return {"type": "tool_result", "tool_use_id": block.id,
                    "content": f"Arguments invalides : {e}", "is_error": True}

    # --- conversation ------------------------------------------------------
    def repondre(self, session_id: str, message: str) -> dict[str, Any]:
        message = (message or "").strip()
        if not message:
            return {"reponse": "Bonjour ! Comment puis-je vous aider ?", "actions": []}
        sess = self._session(session_id)
        with sess.lock:
            if sess.tours >= MAX_USER_TURNS:
                return {"reponse": "Notre echange est long : pour aller plus loin, le plus simple est d'appeler directement le garage. Vous pouvez aussi recommencer une nouvelle conversation.",
                        "actions": []}
            depart = len(sess.messages)
            msgs = sess.messages
            msgs.append({"role": "user", "content": message[:4000]})
            actions: list[dict[str, Any]] = []
            try:
                for _ in range(MAX_TOOL_ROUNDS):
                    resp = self._call(msgs)
                    if resp.stop_reason == "refusal":
                        del msgs[depart:]  # retire uniquement ce tour (fin d'historique)
                        return {"reponse": "Je ne peux pas vous aider sur ce point. Pour toute question sur nos vehicules ou notre atelier, je suis a votre disposition.",
                                "actions": []}
                    msgs.append({"role": "assistant", "content": resp.content})
                    if resp.stop_reason == "pause_turn":
                        continue
                    appels = [b for b in resp.content if b.type == "tool_use"]
                    if resp.stop_reason != "tool_use" or not appels:
                        sess.tours += 1
                        texte = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                        return {"reponse": texte or "Pouvez-vous preciser votre demande ?", "actions": actions}
                    resultats = [self._executer(b) for b in appels]
                    for b, r in zip(appels, resultats):
                        if b.name in ("prendre_rendez_vous", "enregistrer_demande") and not r.get("is_error"):
                            actions.append({"outil": b.name, "resultat": json.loads(r["content"])})
                    msgs.append({"role": "user", "content": resultats})
                log.warning("session %s : trop d'appels d'outils", session_id)
                del msgs[depart:]
                return {"reponse": "Desole, je n'arrive pas a finaliser votre demande. Pouvez-vous reformuler, ou appeler directement le garage ?",
                        "actions": actions}
            except anthropic.APIError:
                log.exception("erreur API Claude")
                del msgs[depart:]
                return {"reponse": "Le service est momentanement indisponible. Merci de reessayer dans un instant ou d'appeler le garage.",
                        "actions": actions, "erreur": True}
