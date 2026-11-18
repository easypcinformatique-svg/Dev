"""Serveur web de l'agent IA AKMS AUTOS.

Lancer :  uvicorn server:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import logging
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agent import AkmsAgent, GestionAgent
from gestion_tools import GestionTools
from store import Store
from tools import GarageTools

logging.basicConfig(level=logging.INFO)

BASE = Path(__file__).parent
CONFIG = Path(os.getenv("AKMS_CONFIG", BASE / "config" / "garage.json"))
STOCK = Path(os.getenv("AKMS_STOCK", BASE / "data" / "vehicules.json"))
DB = os.getenv("AKMS_DB", str(BASE / "data" / "akms.db"))
ADMIN_TOKEN = os.getenv("AKMS_ADMIN_TOKEN", "")
ORIGINS = [o.strip() for o in os.getenv("AKMS_ALLOWED_ORIGINS", "*").split(",") if o.strip()]
RATE_PER_MIN = int(os.getenv("AKMS_RATE_PER_MIN", "20"))


class ChatIn(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    message: str = Field(max_length=4000)


def build_app(agent: AkmsAgent | None = None, store: Store | None = None,
              gestion: GestionAgent | None = None) -> FastAPI:
    store = store or Store(DB)
    agent = agent or AkmsAgent(GarageTools(CONFIG, STOCK, store))
    gestion = gestion or GestionAgent(GestionTools(CONFIG, STOCK, store), client=agent.client)
    app = FastAPI(title="AKMS AUTOS - Agent IA")
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST"],
                       allow_headers=["*"])
    hits: dict[str, deque] = defaultdict(deque)

    def limiter(request: Request) -> None:
        ip = request.client.host if request.client else "?"
        now = time.time()
        q = hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_PER_MIN:
            raise HTTPException(429, "Trop de messages, patientez une minute.")
        q.append(now)

    def admin(authorization: str = Header(default="")) -> None:
        if not ADMIN_TOKEN:
            raise HTTPException(503, "AKMS_ADMIN_TOKEN non configure.")
        if not secrets.compare_digest(authorization, f"Bearer {ADMIN_TOKEN}"):
            raise HTTPException(401, "Non autorise.")

    @app.get("/")
    def page():
        return FileResponse(BASE / "static" / "index.html")

    @app.get("/widget.js")
    def widget():
        return FileResponse(BASE / "static" / "widget.js", media_type="application/javascript")

    @app.get("/sante")
    def sante():
        return {"ok": True}

    @app.post("/api/chat", dependencies=[Depends(limiter)])
    def chat(body: ChatIn):
        return agent.repondre(body.session_id, body.message)

    @app.post("/api/reset", dependencies=[Depends(limiter)])
    def reset(body: ChatIn):
        agent.reset(body.session_id)
        return {"ok": True}

    @app.get("/gestion")
    def page_gestion():
        return FileResponse(BASE / "static" / "gestion.html")

    @app.post("/api/gestion/chat", dependencies=[Depends(admin), Depends(limiter)])
    def chat_gestion(body: ChatIn):
        return gestion.repondre("g-" + body.session_id, body.message)

    @app.post("/api/gestion/reset", dependencies=[Depends(admin)])
    def reset_gestion(body: ChatIn):
        gestion.reset("g-" + body.session_id)
        return {"ok": True}

    @app.get("/admin/ventes", dependencies=[Depends(admin)])
    def liste_ventes():
        return store.lister("ventes")

    @app.get("/admin/journal", dependencies=[Depends(admin)])
    def liste_journal():
        return store.lister("journal")

    @app.get("/admin/rendez-vous", dependencies=[Depends(admin)])
    def liste_rdv():
        return store.lister("rendez_vous")

    @app.get("/admin/demandes", dependencies=[Depends(admin)])
    def liste_demandes():
        return store.lister("demandes")

    return app


app = build_app() if os.getenv("AKMS_NO_AUTOSTART") != "1" else None
