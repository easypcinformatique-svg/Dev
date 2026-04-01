"""Service pour la gestion des creneaux horaires."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Creneau, CreneauConfig


async def get_config(db: AsyncSession):
    result = await db.execute(select(CreneauConfig).order_by(CreneauConfig.jour_semaine))
    return result.scalars().all()


async def save_config(db: AsyncSession, configs: list[dict]):
    # Supprimer l'ancienne config
    result = await db.execute(select(CreneauConfig))
    for c in result.scalars().all():
        await db.delete(c)
    # Creer la nouvelle
    for c in configs:
        db.add(CreneauConfig(**c))
    await db.commit()


async def generer_creneaux_jour(db: AsyncSession, jour: date) -> list[Creneau]:
    """Genere les creneaux pour un jour donne selon la config."""
    jour_semaine = jour.weekday()
    result = await db.execute(
        select(CreneauConfig).where(
            CreneauConfig.jour_semaine == jour_semaine,
            CreneauConfig.actif.is_(True),
        )
    )
    configs = result.scalars().all()

    # Verifier s'il y a deja des creneaux pour ce jour
    existing = await db.execute(
        select(Creneau).where(Creneau.date == jour)
    )
    if existing.scalars().first():
        # Retourner les creneaux existants
        result = await db.execute(
            select(Creneau).where(Creneau.date == jour).order_by(Creneau.heure_debut)
        )
        return list(result.scalars().all())

    creneaux = []
    for config in configs:
        current = datetime.combine(jour, config.heure_debut)
        end = datetime.combine(jour, config.heure_fin)
        delta = timedelta(minutes=config.intervalle_minutes)

        while current + delta <= end:
            creneau = Creneau(
                date=jour,
                heure_debut=current.time(),
                heure_fin=(current + delta).time(),
                capacite_max=config.capacite_max,
                nb_commandes=0,
                verrouille=False,
            )
            db.add(creneau)
            creneaux.append(creneau)
            current += delta

    await db.commit()
    for c in creneaux:
        await db.refresh(c)
    return creneaux


async def get_creneaux_jour(db: AsyncSession, jour: date) -> list[Creneau]:
    """Retourne les creneaux d'un jour, les genere si necessaire."""
    creneaux = await generer_creneaux_jour(db, jour)
    return creneaux


async def get_creneaux_disponibles(db: AsyncSession, jour: date) -> list[Creneau]:
    """Retourne uniquement les creneaux disponibles."""
    creneaux = await get_creneaux_jour(db, jour)
    now = datetime.now().time()
    return [
        c for c in creneaux
        if c.disponible and (jour > date.today() or c.heure_debut > now)
    ]


async def incrementer_creneau(db: AsyncSession, creneau_id: int) -> Creneau | None:
    """Incremente le compteur du creneau avec verrou pour eviter les race conditions."""
    result = await db.execute(
        select(Creneau).where(Creneau.id == creneau_id).with_for_update()
    )
    creneau = result.scalar_one_or_none()
    if not creneau or not creneau.disponible:
        return None
    creneau.nb_commandes += 1
    await db.commit()
    await db.refresh(creneau)
    return creneau


async def decrementer_creneau(db: AsyncSession, creneau_id: int):
    """Decremente le compteur (annulation commande)."""
    result = await db.execute(select(Creneau).where(Creneau.id == creneau_id))
    creneau = result.scalar_one_or_none()
    if creneau and creneau.nb_commandes > 0:
        creneau.nb_commandes -= 1
        await db.commit()


async def verrouiller_creneau(db: AsyncSession, creneau_id: int, verrouille: bool):
    result = await db.execute(select(Creneau).where(Creneau.id == creneau_id))
    creneau = result.scalar_one_or_none()
    if creneau:
        creneau.verrouille = verrouille
        await db.commit()
    return creneau
