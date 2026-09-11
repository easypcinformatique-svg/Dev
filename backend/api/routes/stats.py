"""Routes pour les statistiques."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.api.deps import get_current_user
from backend.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["statistiques"])


@router.get("/")
async def get_stats(
    date_debut: date | None = None,
    date_fin: date | None = None,
    periode: str | None = None,  # "jour", "semaine", "mois"
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    today = date.today()
    if periode == "jour":
        date_debut = today
        date_fin = today
    elif periode == "semaine":
        date_debut = today - timedelta(days=today.weekday())
        date_fin = today
    elif periode == "mois":
        date_debut = today.replace(day=1)
        date_fin = today
    else:
        date_debut = date_debut or today
        date_fin = date_fin or today

    return await stats_service.stats_periode(db, date_debut, date_fin)
