"""Routes pour la gestion des commandes (creation, suivi, historique)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/commandes", tags=["commandes"])
