"""Routes pour la gestion des commandes."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models.enums import Comptoir, StatutCommande
from backend.models.schemas import CommandeCreate, CommandeResponse, CommandeStatusUpdate
from backend.services import commande_service
from backend.websocket.manager import broadcast_order_event

router = APIRouter(prefix="/api/commandes", tags=["commandes"])


@router.post("/", response_model=CommandeResponse)
async def creer_commande(
    req: CommandeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = req.model_dump()
        commande = await commande_service.creer_commande(db, data)
        full = await commande_service.get_commande(db, commande.id)
        # Notifier la cuisine
        await broadcast_order_event("new_order", _commande_to_dict(full))
        return full
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[CommandeResponse])
async def lister_commandes(
    jour: date | None = None,
    comptoir: Comptoir | None = None,
    statut: StatutCommande | None = None,
    creneau_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await commande_service.lister_commandes(
        db, jour=jour, comptoir=comptoir, statut=statut, creneau_id=creneau_id
    )


@router.get("/{commande_id}", response_model=CommandeResponse)
async def get_commande(commande_id: int, db: AsyncSession = Depends(get_db)):
    commande = await commande_service.get_commande(db, commande_id)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvee")
    return commande


@router.get("/numero/{numero}", response_model=CommandeResponse)
async def get_par_numero(numero: str, db: AsyncSession = Depends(get_db)):
    commande = await commande_service.get_commande_par_numero(db, numero)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvee")
    return commande


@router.patch("/{commande_id}/statut", response_model=CommandeResponse)
async def changer_statut(
    commande_id: int,
    req: CommandeStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    commande = await commande_service.changer_statut(db, commande_id, req.statut)
    if not commande:
        raise HTTPException(status_code=404, detail="Commande non trouvee")
    full = await commande_service.get_commande(db, commande.id)
    await broadcast_order_event("order_status_changed", _commande_to_dict(full))
    return full


@router.delete("/{commande_id}")
async def annuler_commande(
    commande_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not await commande_service.annuler_commande(db, commande_id):
        raise HTTPException(status_code=404, detail="Commande non trouvee")
    await broadcast_order_event("order_cancelled", {"commande_id": commande_id})
    return {"ok": True}


def _commande_to_dict(c) -> dict:
    """Serialise une commande pour le broadcast WS."""
    return {
        "id": c.id,
        "numero": c.numero,
        "comptoir": c.comptoir.value,
        "mode": c.mode.value,
        "statut": c.statut.value,
        "montant_ttc": c.montant_ttc,
        "notes": c.notes,
        "creneau_label": c.creneau.label if c.creneau else None,
        "client_nom": c.client.nom if c.client else None,
        "adresse_livraison": c.adresse_livraison,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "lignes": [
            {
                "produit_nom": l.produit.nom if l.produit else "",
                "taille": l.taille.taille.value if l.taille else None,
                "quantite": l.quantite,
                "notes": l.notes,
                "supplements": [
                    {"nom": s.supplement.nom if s.supplement else "", "quantite": s.quantite}
                    for s in (l.supplements or [])
                ],
            }
            for l in (c.lignes or [])
        ],
    }
