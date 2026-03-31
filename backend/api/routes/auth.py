"""Routes pour l'authentification (login PIN, gestion utilisateurs, roles)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user, require_admin
from backend.models.schemas import (
    LoginRequest, TokenResponse, UtilisateurCreate, UtilisateurResponse,
)
from backend.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate(db, req.pin)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="PIN incorrect")
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
