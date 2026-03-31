"""Routes pour la gestion des clients."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.database import get_db
from backend.models import Client, Commande
from backend.models.schemas import ClientCreate, ClientResponse, CommandeResponse

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("/", response_model=list[ClientResponse])
async def search_clients(
    telephone: str | None = None,
    nom: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Client)
    if telephone:
        stmt = stmt.where(Client.telephone.contains(telephone))
    if nom:
        stmt = stmt.where(Client.nom.ilike(f"%{nom}%"))
    stmt = stmt.limit(20)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=ClientResponse)
async def create_client(req: ClientCreate, db: AsyncSession = Depends(get_db)):
    # Verifier si telephone existe deja
    result = await db.execute(select(Client).where(Client.telephone == req.telephone))
    existing = result.scalar_one_or_none()
    if existing:
        for k, v in req.model_dump(exclude_none=True).items():
            setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return existing
    client = Client(**req.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouve")
    return client


@router.get("/{client_id}/historique", response_model=list[CommandeResponse])
async def get_historique(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Commande)
        .options(
            selectinload(Commande.lignes),
            selectinload(Commande.creneau),
        )
        .where(Commande.client_id == client_id)
        .order_by(Commande.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()
