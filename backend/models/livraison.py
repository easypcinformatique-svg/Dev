"""Modeles pour la gestion des livraisons."""

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin
from .enums import StatutLivreur


class Livreur(Base, TimestampMixin):
    __tablename__ = "livreurs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), nullable=False)
    statut: Mapped[StatutLivreur] = mapped_column(
        Enum(StatutLivreur), default=StatutLivreur.DISPONIBLE
    )
    actif: Mapped[bool] = mapped_column(Boolean, default=True)


class ZoneLivraison(Base, TimestampMixin):
    __tablename__ = "zones_livraison"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    codes_postaux: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    rayon_km: Mapped[float | None] = mapped_column(Float)
    frais_livraison: Mapped[float] = mapped_column(Float, default=0.0)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
