"""Routes pour la gestion des livraisons."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models.schemas import (
    LivreurCreate, LivreurResponse,
    ZoneLivraisonCreate, ZoneLivraisonResponse,
    AssignerLivreurRequest, CommandeResponse,
)
from backend.services import livraison_service

router = APIRouter(prefix="/api/livraisons", tags=["livraisons"])


@router.get("/en-attente", response_model=list[CommandeResponse])
async def commandes_a_livrer(db: AsyncSession = Depends(get_db)):
    return await livraison_service.get_commandes_a_livrer(db)


@router.post("/assigner")
async def assigner_livreur(
    req: AssignerLivreurRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    commande = await livraison_service.assigner_livreur(db, req.commande_id, req.livreur_id)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande ou livreur introuvable")
    return {"ok": True, "statut": commande.statut.value}


@router.patch("/{commande_id}/livree")
async def marquer_livree(
    commande_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    commande = await livraison_service.marquer_livree(db, commande_id)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return {"ok": True}


@router.get("/livreurs", response_model=list[LivreurResponse])
async def get_livreurs(db: AsyncSession = Depends(get_db)):
    return await livraison_service.get_livreurs(db)


@router.post("/livreurs", response_model=LivreurResponse)
async def create_livreur(
    req: LivreurCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await livraison_service.create_livreur(db, **req.model_dump())


@router.get("/zones", response_model=list[ZoneLivraisonResponse])
async def get_zones(db: AsyncSession = Depends(get_db)):
    return await livraison_service.get_zones(db)


@router.post("/zones", response_model=ZoneLivraisonResponse)
async def create_zone(
    req: ZoneLivraisonCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await livraison_service.create_zone(db, **req.model_dump())


@router.get("/frais")
async def get_frais(code_postal: str, db: AsyncSession = Depends(get_db)):
    frais = await livraison_service.get_frais_livraison(db, code_postal)
    return {"frais_livraison": frais}
