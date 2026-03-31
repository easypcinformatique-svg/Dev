"""Routes pour la gestion des livraisons (livreurs, zones, suivi)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/livraisons", tags=["livraisons"])
