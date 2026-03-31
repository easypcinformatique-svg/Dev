"""Modeles pour les commandes, clients et paiements."""

from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import (
    Comptoir, ModeCommande, ModePaiement, StatutCommande, StatutPaiement,
)


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    adresse: Mapped[str | None] = mapped_column(Text)
    code_postal: Mapped[str | None] = mapped_column(String(10))
    ville: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    commandes: Mapped[list["Commande"]] = relationship(back_populates="client", lazy="selectin")


class Commande(Base, TimestampMixin):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    comptoir: Mapped[Comptoir] = mapped_column(Enum(Comptoir), nullable=False)
    mode: Mapped[ModeCommande] = mapped_column(Enum(ModeCommande), nullable=False)
    statut: Mapped[StatutCommande] = mapped_column(
        Enum(StatutCommande), default=StatutCommande.NOUVELLE
    )
    creneau_id: Mapped[int | None] = mapped_column(ForeignKey("creneaux.id"))

    # Montants
    montant_ht: Mapped[float] = mapped_column(Float, default=0.0)
    montant_tva: Mapped[float] = mapped_column(Float, default=0.0)
    montant_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    frais_livraison: Mapped[float] = mapped_column(Float, default=0.0)
    remise: Mapped[float] = mapped_column(Float, default=0.0)

    # Livraison
    adresse_livraison: Mapped[str | None] = mapped_column(Text)
    livreur_id: Mapped[int | None] = mapped_column(ForeignKey("livreurs.id"))

    # Paiement
    mode_paiement: Mapped[ModePaiement | None] = mapped_column(Enum(ModePaiement))
    statut_paiement: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement), default=StatutPaiement.EN_ATTENTE
    )
    stripe_payment_id: Mapped[str | None] = mapped_column(String(200))

    # Meta
    notes: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))
    whatsapp_conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations_wa.id")
    )

    # Relations
    client: Mapped["Client | None"] = relationship(back_populates="commandes")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", lazy="selectin", cascade="all, delete-orphan"
    )
    creneau: Mapped["Creneau | None"] = relationship()
    livreur: Mapped["Livreur | None"] = relationship()
    utilisateur: Mapped["Utilisateur | None"] = relationship()
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", lazy="selectin"
    )


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), nullable=False)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"), nullable=False)
    taille_id: Mapped[int | None] = mapped_column(ForeignKey("produit_tailles.id"))
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix_unitaire: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    produit: Mapped["Produit"] = relationship()
    taille: Mapped["ProduitTaille | None"] = relationship()
    supplements: Mapped[list["LigneCommandeSupplement"]] = relationship(
        back_populates="ligne", lazy="selectin", cascade="all, delete-orphan"
    )


class LigneCommandeSupplement(Base):
    __tablename__ = "lignes_commande_supplements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ligne_id: Mapped[int] = mapped_column(ForeignKey("lignes_commande.id"), nullable=False)
    supplement_id: Mapped[int] = mapped_column(ForeignKey("supplements.id"), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix: Mapped[float] = mapped_column(Float, nullable=False)

    ligne: Mapped["LigneCommande"] = relationship(back_populates="supplements")
    supplement: Mapped["Supplement"] = relationship()


class Paiement(Base, TimestampMixin):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id"), nullable=False)
    mode: Mapped[ModePaiement] = mapped_column(Enum(ModePaiement), nullable=False)
    montant: Mapped[float] = mapped_column(Float, nullable=False)
    rendu_monnaie: Mapped[float] = mapped_column(Float, default=0.0)

    commande: Mapped["Commande"] = relationship(back_populates="paiements")


# Imports circulaires resolus via string references
from .creneau import Creneau  # noqa: E402, F401
from .utilisateur import Utilisateur  # noqa: E402, F401
from .livraison import Livreur  # noqa: E402, F401
from .menu import Produit, ProduitTaille, Supplement  # noqa: E402, F401
from .whatsapp import ConversationWA  # noqa: E402, F401
