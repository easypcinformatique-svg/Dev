"""Routes pour les statistiques et rapports (CA, top pizzas, performance)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/stats", tags=["statistiques"])
