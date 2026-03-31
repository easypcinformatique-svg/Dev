"""Routes pour la gestion des clients (recherche, historique, fidélité)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/clients", tags=["clients"])
