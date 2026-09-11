"""Modeles pour les conversations WhatsApp."""

from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin
from .enums import EtapeWhatsApp


class ConversationWA(Base, TimestampMixin):
    __tablename__ = "conversations_wa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telephone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    etape: Mapped[EtapeWhatsApp] = mapped_column(
        Enum(EtapeWhatsApp), default=EtapeWhatsApp.ACCUEIL
    )
    panier_json: Mapped[str | None] = mapped_column(Text)  # JSON du panier en cours
    creneau_id: Mapped[int | None] = mapped_column(Integer)
    mode: Mapped[str | None] = mapped_column(String(20))  # emporter / livraison
    adresse: Mapped[str | None] = mapped_column(Text)
