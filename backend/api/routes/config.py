"""Routes pour la configuration (infos pizzeria, horaires, promos, imprimantes)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["configuration"])
