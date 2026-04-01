"""Service pour la gestion du menu."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    Categorie, Produit, ProduitTaille, Supplement, Formule, FormuleElement,
)


# ── Categories ────────────────────────────────────────────────

async def get_categories(db: AsyncSession, actif_only: bool = False):
    stmt = select(Categorie).options(
        selectinload(Categorie.produits).selectinload(Produit.tailles)
    ).order_by(Categorie.ordre)
    if actif_only:
        stmt = stmt.where(Categorie.actif.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_categorie(db: AsyncSession, **kwargs) -> Categorie:
    cat = Categorie(**kwargs)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def update_categorie(db: AsyncSession, cat_id: int, **kwargs) -> Categorie | None:
    result = await db.execute(select(Categorie).where(Categorie.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    return cat


async def delete_categorie(db: AsyncSession, cat_id: int) -> bool:
    result = await db.execute(select(Categorie).where(Categorie.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        return False
    await db.delete(cat)
    await db.commit()
    return True


# ── Produits ──────────────────────────────────────────────────

async def get_produits(db: AsyncSession, categorie_id: int | None = None, actif_only: bool = False):
    stmt = select(Produit).options(selectinload(Produit.tailles)).order_by(Produit.ordre)
    if categorie_id:
        stmt = stmt.where(Produit.categorie_id == categorie_id)
    if actif_only:
        stmt = stmt.where(Produit.actif.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_produit(db: AsyncSession, produit_id: int) -> Produit | None:
    result = await db.execute(
        select(Produit).options(selectinload(Produit.tailles))
        .where(Produit.id == produit_id)
    )
    return result.scalar_one_or_none()


async def create_produit(db: AsyncSession, tailles_data: list[dict], **kwargs) -> Produit:
    produit = Produit(**kwargs)
    db.add(produit)
    await db.flush()
    for t in tailles_data:
        taille = ProduitTaille(produit_id=produit.id, **t)
        db.add(taille)
    await db.commit()
    await db.refresh(produit)
    return produit


async def update_produit(db: AsyncSession, produit_id: int, **kwargs) -> Produit | None:
    result = await db.execute(
        select(Produit).options(selectinload(Produit.tailles))
        .where(Produit.id == produit_id)
    )
    produit = result.scalar_one_or_none()
    if not produit:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(produit, k, v)
    await db.commit()
    await db.refresh(produit)
    return produit


async def delete_produit(db: AsyncSession, produit_id: int) -> bool:
    result = await db.execute(select(Produit).where(Produit.id == produit_id))
    produit = result.scalar_one_or_none()
    if not produit:
        return False
    await db.delete(produit)
    await db.commit()
    return True


async def toggle_produit(db: AsyncSession, produit_id: int, actif: bool) -> Produit | None:
    return await update_produit(db, produit_id, actif=actif)


# ── Supplements ───────────────────────────────────────────────

async def get_supplements(db: AsyncSession, actif_only: bool = False):
    stmt = select(Supplement).order_by(Supplement.nom)
    if actif_only:
        stmt = stmt.where(Supplement.actif.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_supplement(db: AsyncSession, **kwargs) -> Supplement:
    sup = Supplement(**kwargs)
    db.add(sup)
    await db.commit()
    await db.refresh(sup)
    return sup


async def update_supplement(db: AsyncSession, sup_id: int, **kwargs) -> Supplement | None:
    result = await db.execute(select(Supplement).where(Supplement.id == sup_id))
    sup = result.scalar_one_or_none()
    if not sup:
        return None
    for k, v in kwargs.items():
        if v is not None:
            setattr(sup, k, v)
    await db.commit()
    await db.refresh(sup)
    return sup


async def delete_supplement(db: AsyncSession, sup_id: int) -> bool:
    result = await db.execute(select(Supplement).where(Supplement.id == sup_id))
    sup = result.scalar_one_or_none()
    if not sup:
        return False
    await db.delete(sup)
    await db.commit()
    return True


# ── Formules ──────────────────────────────────────────────────

async def get_formules(db: AsyncSession, actif_only: bool = False):
    stmt = select(Formule).options(selectinload(Formule.elements))
    if actif_only:
        stmt = stmt.where(Formule.actif.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_formule(db: AsyncSession, elements_data: list[dict], **kwargs) -> Formule:
    formule = Formule(**kwargs)
    db.add(formule)
    await db.flush()
    for e in elements_data:
        elem = FormuleElement(formule_id=formule.id, **e)
        db.add(elem)
    await db.commit()
    await db.refresh(formule)
    return formule
