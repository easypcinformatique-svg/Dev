"""Routes pour la gestion des creneaux horaires."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models.schemas import CreneauResponse, CreneauConfigCreate, CreneauConfigResponse
from backend.services import creneau_service

router = APIRouter(prefix="/api/creneaux", tags=["creneaux"])


@router.get("/", response_model=list[CreneauResponse])
async def get_creneaux(
    jour: date | None = None,
    disponibles_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    jour = jour or date.today()
    if disponibles_only:
        return await creneau_service.get_creneaux_disponibles(db, jour)
    return await creneau_service.get_creneaux_jour(db, jour)


@router.get("/config", response_model=list[CreneauConfigResponse])
async def get_config(db: AsyncSession = Depends(get_db)):
    return await creneau_service.get_config(db)


@router.put("/config")
async def save_config(
    configs: list[CreneauConfigCreate],
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    await creneau_service.save_config(db, [c.model_dump() for c in configs])
    return {"ok": True}


@router.patch("/{creneau_id}/verrouiller")
async def verrouiller(
    creneau_id: int,
    verrouille: bool = True,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    creneau = await creneau_service.verrouiller_creneau(db, creneau_id, verrouille)
    if not creneau:
        raise HTTPException(status_code=404, detail="Creneau non trouve")
    return {"ok": True, "verrouille": creneau.verrouille}
