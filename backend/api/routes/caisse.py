"""Routes pour l'encaissement."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models.schemas import EncaissementRequest, TicketZResponse
from backend.services import caisse_service

router = APIRouter(prefix="/api/caisse", tags=["caisse"])


@router.post("/encaisser")
async def encaisser(
    req: EncaissementRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    try:
        paiements = [{"mode": p.mode, "montant": p.montant} for p in req.paiements]
        commande = await caisse_service.encaisser(
            db, req.commande_id, paiements, req.montant_recu_especes
        )
        return {
            "ok": True,
            "statut_paiement": commande.statut_paiement.value,
            "montant_ttc": commande.montant_ttc,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/ticket-z", response_model=TicketZResponse)
async def get_ticket_z(
    jour: date | None = None,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    jour = jour or date.today()
    return await caisse_service.ticket_z(db, jour)
