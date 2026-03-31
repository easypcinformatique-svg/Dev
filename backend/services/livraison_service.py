"""Service pour la gestion des livraisons."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models import (
    Commande, Livreur, ZoneLivraison,
    ModeCommande, StatutCommande, StatutLivreur,
)


async def get_livreurs(db: AsyncSession, actif_only: bool = True):
    stmt = select(Livreur).order_by(Livreur.nom)
    if actif_only:
        stmt = stmt.where(Livreur.actif.is_(True))
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_livreur(db: AsyncSession, **kwargs) -> Livreur:
    livreur = Livreur(**kwargs)
    db.add(livreur)
    await db.commit()
    await db.refresh(livreur)
    return livreur


async def get_commandes_a_livrer(db: AsyncSession) -> list[Commande]:
    result = await db.execute(
        select(Commande)
        .options(selectinload(Commande.client), selectinload(Commande.creneau))
        .where(
            Commande.mode == ModeCommande.LIVRAISON,
            Commande.statut.in_([StatutCommande.PRETE]),
        )
        .order_by(Commande.created_at)
    )
    return list(result.scalars().all())


async def assigner_livreur(
    db: AsyncSession, commande_id: int, livreur_id: int
) -> Commande | None:
    result = await db.execute(select(Commande).where(Commande.id == commande_id))
    commande = result.scalar_one_or_none()
    if not commande:
        return None

    result = await db.execute(select(Livreur).where(Livreur.id == livreur_id))
    livreur = result.scalar_one_or_none()
    if not livreur:
        return None

    commande.livreur_id = livreur_id
    commande.statut = StatutCommande.EN_LIVRAISON
    livreur.statut = StatutLivreur.EN_COURSE

    await db.commit()
    await db.refresh(commande)
    return commande


async def marquer_livree(db: AsyncSession, commande_id: int) -> Commande | None:
    result = await db.execute(
        select(Commande).where(Commande.id == commande_id)
    )
    commande = result.scalar_one_or_none()
    if not commande:
        return None

    commande.statut = StatutCommande.LIVREE

    if commande.livreur_id:
        result = await db.execute(
            select(Livreur).where(Livreur.id == commande.livreur_id)
        )
        livreur = result.scalar_one_or_none()
        if livreur:
            livreur.statut = StatutLivreur.DISPONIBLE

    await db.commit()
    await db.refresh(commande)
    return commande


async def get_zones(db: AsyncSession):
    result = await db.execute(
        select(ZoneLivraison).where(ZoneLivraison.actif.is_(True))
    )
    return result.scalars().all()


async def create_zone(db: AsyncSession, **kwargs) -> ZoneLivraison:
    zone = ZoneLivraison(**kwargs)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


async def get_frais_livraison(db: AsyncSession, code_postal: str) -> float:
    """Calcule les frais de livraison selon le code postal."""
    result = await db.execute(
        select(ZoneLivraison).where(ZoneLivraison.actif.is_(True))
    )
    zones = result.scalars().all()
    for zone in zones:
        if zone.codes_postaux and code_postal in zone.codes_postaux:
            return zone.frais_livraison
    return 0.0
