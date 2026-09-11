"""Routes pour la gestion des stocks."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models import Ingredient

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/ingredients")
async def get_ingredients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ingredient).order_by(Ingredient.nom))
    ingredients = result.scalars().all()
    return [
        {
            "id": i.id,
            "nom": i.nom,
            "unite": i.unite,
            "quantite_stock": i.quantite_stock,
            "seuil_alerte": i.seuil_alerte,
            "alerte": i.quantite_stock <= i.seuil_alerte,
        }
        for i in ingredients
    ]


@router.get("/alertes")
async def get_alertes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Ingredient).order_by(Ingredient.nom))
    ingredients = result.scalars().all()
    return [
        {
            "id": i.id,
            "nom": i.nom,
            "unite": i.unite,
            "quantite_stock": i.quantite_stock,
            "seuil_alerte": i.seuil_alerte,
        }
        for i in ingredients
        if i.quantite_stock <= i.seuil_alerte
    ]


@router.post("/ingredients")
async def create_ingredient(
    nom: str,
    unite: str = "unite",
    quantite_stock: float = 0,
    seuil_alerte: float = 5,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    ingredient = Ingredient(
        nom=nom, unite=unite, quantite_stock=quantite_stock, seuil_alerte=seuil_alerte
    )
    db.add(ingredient)
    await db.commit()
    await db.refresh(ingredient)
    return {"id": ingredient.id, "nom": ingredient.nom}


@router.patch("/ingredients/{ingredient_id}/stock")
async def update_stock(
    ingredient_id: int,
    quantite: float,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Ingredient).where(Ingredient.id == ingredient_id))
    ingredient = result.scalar_one_or_none()
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient non trouve")
    ingredient.quantite_stock = quantite
    await db.commit()
    return {"ok": True, "quantite_stock": ingredient.quantite_stock}
