"""Point d'entree de l'application PizzaCaisse."""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.database import engine
from backend.models.base import Base
import backend.models  # noqa: F401 - register all models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cree les tables et seed au demarrage."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _auto_seed()
    yield


async def _auto_seed():
    """Seed auto si DB vide."""
    try:
        from backend.db.database import async_session
        from backend.models import Utilisateur
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(Utilisateur).limit(1))
            if result.scalar_one_or_none() is not None:
                return

        from backend.db.seed import seed
        await seed()
        print("Auto-seed completed.")
    except Exception as e:
        print(f"Auto-seed error (non-fatal): {e}")


app = FastAPI(
    title="PizzaCaisse API",
    description="API du logiciel de caisse pour pizzeria (emporter & livraison)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes API ────────────────────────────────────────────────
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

for r in [auth_router, menu_router, commandes_router, clients_router,
          creneaux_router, caisse_router, livraisons_router, stats_router,
          stocks_router, config_router, whatsapp_router]:
    app.include_router(r)

# ── WebSocket ─────────────────────────────────────────────────
from backend.websocket.manager import websocket_endpoint
app.add_api_websocket_route("/ws/kitchen", websocket_endpoint)


# ── Endpoints utilitaires ─────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pizzacaisse-api", "version": "1.0.0"}


@app.post("/api/seed")
async def run_seed(force: bool = False):
    """Initialise la DB avec les donnees demo."""
    try:
        from backend.db.database import async_session
        from backend.models import Utilisateur
        from sqlalchemy import select

        if force:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
        else:
            async with async_session() as db:
                result = await db.execute(select(Utilisateur).limit(1))
                if result.scalar_one_or_none() is not None:
                    return {"status": "already_seeded", "hint": "Use ?force=true to reset"}

        from backend.db.seed import seed
        await seed()
        return {"status": "seeded", "users": "Admin:1234, Caissier:5678, Pizzaiolo:9999, Livreur:1111"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Frontend SPA (doit etre en DERNIER) ───────────────────────
static_dir = Path(__file__).resolve().parent.parent / "static"

if static_dir.exists() and (static_dir / "index.html").exists():
    from fastapi.staticfiles import StaticFiles

    # Servir /assets/* directement
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Catch-all pour le SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = static_dir / full_path
        if file_path.is_file() and ".." not in full_path:
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
