"""Routes pour la gestion du menu (pizzas, categories, supplements, formules)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.models.schemas import (
    CategorieCreate, CategorieResponse,
    ProduitCreate, ProduitUpdate, ProduitResponse,
    SupplementCreate, SupplementResponse,
    FormuleCreate, FormuleResponse,
)
from backend.services import menu_service

router = APIRouter(prefix="/api/menu", tags=["menu"])


# ── Menu complet ──────────────────────────────────────────────

@router.get("/", response_model=list[CategorieResponse])
async def get_menu(actif: bool = True, db: AsyncSession = Depends(get_db)):
    """Retourne le menu complet (categories + produits + tailles)."""
    return await menu_service.get_categories(db, actif_only=actif)


# ── Categories ────────────────────────────────────────────────

@router.post("/categories", response_model=CategorieResponse)
async def create_categorie(
    req: CategorieCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await menu_service.create_categorie(db, **req.model_dump())


@router.put("/categories/{cat_id}", response_model=CategorieResponse)
async def update_categorie(
    cat_id: int,
    req: CategorieCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    cat = await menu_service.update_categorie(db, cat_id, **req.model_dump())
    if not cat:
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    return cat


@router.delete("/categories/{cat_id}")
async def delete_categorie(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not await menu_service.delete_categorie(db, cat_id):
        raise HTTPException(status_code=404, detail="Categorie non trouvee")
    return {"ok": True}


# ── Produits ──────────────────────────────────────────────────

@router.get("/produits", response_model=list[ProduitResponse])
async def get_produits(
    categorie_id: int | None = None,
    actif: bool = True,
    db: AsyncSession = Depends(get_db),
):
    return await menu_service.get_produits(db, categorie_id, actif_only=actif)


@router.post("/produits", response_model=ProduitResponse)
async def create_produit(
    req: ProduitCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    tailles = [t.model_dump() for t in req.tailles]
    data = req.model_dump(exclude={"tailles"})
    return await menu_service.create_produit(db, tailles_data=tailles, **data)


@router.put("/produits/{produit_id}", response_model=ProduitResponse)
async def update_produit(
    produit_id: int,
    req: ProduitUpdate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    produit = await menu_service.update_produit(
        db, produit_id, **req.model_dump(exclude_none=True)
    )
    if not produit:
        raise HTTPException(status_code=404, detail="Produit non trouve")
    return produit


@router.patch("/produits/{produit_id}/disponibilite")
async def toggle_disponibilite(
    produit_id: int,
    actif: bool,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    produit = await menu_service.toggle_produit(db, produit_id, actif)
    if not produit:
        raise HTTPException(status_code=404, detail="Produit non trouve")
    return {"ok": True, "actif": produit.actif}


@router.delete("/produits/{produit_id}")
async def delete_produit(
    produit_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not await menu_service.delete_produit(db, produit_id):
        raise HTTPException(status_code=404, detail="Produit non trouve")
    return {"ok": True}


# ── Supplements ───────────────────────────────────────────────

@router.get("/supplements", response_model=list[SupplementResponse])
async def get_supplements(actif: bool = True, db: AsyncSession = Depends(get_db)):
    return await menu_service.get_supplements(db, actif_only=actif)


@router.post("/supplements", response_model=SupplementResponse)
async def create_supplement(
    req: SupplementCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    return await menu_service.create_supplement(db, **req.model_dump())


@router.put("/supplements/{sup_id}", response_model=SupplementResponse)
async def update_supplement(
    sup_id: int,
    req: SupplementCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    sup = await menu_service.update_supplement(db, sup_id, **req.model_dump())
    if not sup:
        raise HTTPException(status_code=404, detail="Supplement non trouve")
    return sup


@router.delete("/supplements/{sup_id}")
async def delete_supplement(
    sup_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not await menu_service.delete_supplement(db, sup_id):
        raise HTTPException(status_code=404, detail="Supplement non trouve")
    return {"ok": True}


# ── Formules ──────────────────────────────────────────────────

@router.get("/formules", response_model=list[FormuleResponse])
async def get_formules(actif: bool = True, db: AsyncSession = Depends(get_db)):
    return await menu_service.get_formules(db, actif_only=actif)


@router.post("/formules", response_model=FormuleResponse)
async def create_formule(
    req: FormuleCreate,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    elements = [e.model_dump() for e in req.elements]
    data = req.model_dump(exclude={"elements"})
    return await menu_service.create_formule(db, elements_data=elements, **data)
