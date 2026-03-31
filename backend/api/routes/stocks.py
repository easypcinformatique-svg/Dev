"""Routes pour la gestion des stocks (ingredients, alertes, fiches techniques)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/stocks", tags=["stocks"])
