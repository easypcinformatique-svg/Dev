"""Point d'entree de l'application PizzaCaisse."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ajouter le parent au path pour les imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import engine
from backend.models.base import Base

# Import de tous les modeles pour que SQLAlchemy les enregistre
import backend.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cree les tables et seed les donnees au demarrage."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-seed si la DB est vide
    await _auto_seed()
    yield


async def _auto_seed():
    """Insere les donnees de demo si aucun utilisateur n'existe."""
    try:
        from backend.db.database import async_session
        from backend.models import Utilisateur
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(Utilisateur).limit(1))
            if result.scalar_one_or_none() is not None:
                print("DB already seeded, skipping.")
                return

        from backend.db.seed import seed
        await seed()
    except Exception as e:
        print(f"Auto-seed error (non-fatal): {e}")


app = FastAPI(
    title="PizzaCaisse API",
    description="API du logiciel de caisse pour pizzeria (emporter & livraison)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Enregistrement des routes ─────────────────────────────────
from backend.api.routes.auth import router as auth_router
from backend.api.routes.menu import router as menu_router
from backend.api.routes.commandes import router as commandes_router
from backend.api.routes.clients import router as clients_router
from backend.api.routes.creneaux import router as creneaux_router
from backend.api.routes.caisse import router as caisse_router
from backend.api.routes.livraisons import router as livraisons_router
from backend.api.routes.stats import router as stats_router
from backend.api.routes.stocks import router as stocks_router
from backend.api.routes.config import router as config_router
from backend.api.routes.whatsapp import router as whatsapp_router

app.include_router(auth_router)
app.include_router(menu_router)
app.include_router(commandes_router)
app.include_router(clients_router)
app.include_router(creneaux_router)
app.include_router(caisse_router)
app.include_router(livraisons_router)
app.include_router(stats_router)
app.include_router(stocks_router)
app.include_router(config_router)
app.include_router(whatsapp_router)

# ── WebSocket ─────────────────────────────────────────────────
from backend.websocket.manager import websocket_endpoint

app.add_api_websocket_route("/ws/kitchen", websocket_endpoint)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pizzacaisse-api"}


# ── Servir le frontend en production ──────────────────────────
static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
