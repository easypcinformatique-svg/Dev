"""Routes pour l'authentification (login PIN, gestion utilisateurs, roles)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])
