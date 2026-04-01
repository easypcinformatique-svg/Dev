"""Modeles pour la gestion des creneaux horaires."""

from datetime import date, time

from sqlalchemy import Boolean, Date, Float, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class CreneauConfig(Base, TimestampMixin):
    """Configuration des creneaux par jour de semaine."""
    __tablename__ = "creneaux_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jour_semaine: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=lundi, 6=dimanche
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
    intervalle_minutes: Mapped[int] = mapped_column(Integer, default=15)
    capacite_max: Mapped[int] = mapped_column(Integer, default=10)  # max commandes par creneau
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class Creneau(Base):
    """Instance de creneau pour un jour donne."""
    __tablename__ = "creneaux"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    heure_debut: Mapped[time] = mapped_column(Time, nullable=False)
    heure_fin: Mapped[time] = mapped_column(Time, nullable=False)
    capacite_max: Mapped[int] = mapped_column(Integer, default=10)
    nb_commandes: Mapped[int] = mapped_column(Integer, default=0)
    verrouille: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def disponible(self) -> bool:
        return not self.verrouille and self.nb_commandes < self.capacite_max

    @property
    def label(self) -> str:
        start = str(self.heure_debut)[:5] if self.heure_debut else "??:??"
        end = str(self.heure_fin)[:5] if self.heure_fin else "??:??"
        return f"{start}-{end}"
