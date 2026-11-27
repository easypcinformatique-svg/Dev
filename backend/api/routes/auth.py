"""Routes pour l'authentification (login PIN, gestion utilisateurs, roles)."""

import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user, require_admin
from backend.models.schemas import (
    LoginRequest, TokenResponse, UtilisateurCreate, UtilisateurResponse,
)
from backend.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Limitation des tentatives de login par adresse IP (en memoire, par processus)
MAX_ECHECS = 5
FENETRE_SECONDES = 300
_echecs: dict[str, list[float]] = {}


def _echecs_recents(ip: str) -> list[float]:
    maintenant = time.monotonic()
    recents = [t for t in _echecs.get(ip, []) if maintenant - t < FENETRE_SECONDES]
    if recents:
        _echecs[ip] = recents
    else:
        _echecs.pop(ip, None)
    return recents


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, req: LoginRequest, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else "inconnu"
    if len(_echecs_recents(ip)) >= MAX_ECHECS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives, reessayez dans quelques minutes",
        )
    user = await auth_service.authenticate(db, req.pin)
    if not user:
        _echecs.setdefault(ip, []).append(time.monotonic())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PIN incorrect")
    _echecs.pop(ip, None)
    token = auth_service.create_access_token(user.id, user.role.value)
    return TokenResponse(
        access_token=token,
        utilisateur=UtilisateurResponse.model_validate(user),
    )


@router.get("/me", response_model=UtilisateurResponse)
async def me(user=Depends(get_current_user)):
    return UtilisateurResponse.model_validate(user)


@router.post("/utilisateurs", response_model=UtilisateurResponse)
async def create_user(
    req: UtilisateurCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_admin),
):
    user = await auth_service.create_utilisateur(db, req.nom, req.pin, req.role)
    return UtilisateurResponse.model_validate(user)
