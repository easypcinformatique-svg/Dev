"""Modeles pour les commandes, clients, fidelite et paiements."""

from sqlalchemy import (
    Boolean, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import (
    Comptoir, ModeCommande, ModePaiement, StatutCommande, StatutPaiement, TypePate,
)


class Client(Base, TimestampMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    telephone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(200))
    adresse: Mapped[str | None] = mapped_column(Text)
    code_postal: Mapped[str | None] = mapped_column(String(10))
    ville: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    # Fidelite
    points_fidelite: Mapped[int] = mapped_column(Integer, default=0)
    nb_commandes: Mapped[int] = mapped_column(Integer, default=0)

    commandes: Mapped[list["Commande"]] = relationship(
        back_populates="client", lazy="selectin"
    )


class Commande(Base, TimestampMixin):
    __tablename__ = "commandes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    comptoir: Mapped[Comptoir] = mapped_column(Enum(Comptoir), nullable=False, index=True)
    mode: Mapped[ModeCommande] = mapped_column(Enum(ModeCommande), nullable=False)
    statut: Mapped[StatutCommande] = mapped_column(
        Enum(StatutCommande), default=StatutCommande.NOUVELLE, index=True
    )
    creneau_id: Mapped[int | None] = mapped_column(ForeignKey("creneaux.id"))

    # Montants
    montant_ht: Mapped[float] = mapped_column(Float, default=0.0)
    montant_tva: Mapped[float] = mapped_column(Float, default=0.0)
    montant_ttc: Mapped[float] = mapped_column(Float, default=0.0)
    frais_livraison: Mapped[float] = mapped_column(Float, default=0.0)
    remise: Mapped[float] = mapped_column(Float, default=0.0)
    code_promo: Mapped[str | None] = mapped_column(String(50))

    # Livraison
    adresse_livraison: Mapped[str | None] = mapped_column(Text)
    livreur_id: Mapped[int | None] = mapped_column(ForeignKey("livreurs.id"))

    # Paiement
    mode_paiement: Mapped[ModePaiement | None] = mapped_column(Enum(ModePaiement))
    statut_paiement: Mapped[StatutPaiement] = mapped_column(
        Enum(StatutPaiement), default=StatutPaiement.EN_ATTENTE
    )
    stripe_payment_id: Mapped[str | None] = mapped_column(String(200))

    # Temps
    temps_estime: Mapped[int | None] = mapped_column(Integer)  # minutes
    temps_reel: Mapped[int | None] = mapped_column(Integer)  # minutes

    # Meta
    notes: Mapped[str | None] = mapped_column(Text)
    utilisateur_id: Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id"))

    # Relations
    client: Mapped["Client | None"] = relationship(back_populates="commandes")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", lazy="selectin", cascade="all, delete-orphan"
    )
    creneau = relationship("Creneau", lazy="selectin")
    livreur = relationship("Livreur", lazy="selectin")
    utilisateur = relationship("Utilisateur", lazy="selectin")
    paiements: Mapped[list["Paiement"]] = relationship(
        back_populates="commande", lazy="selectin"
    )


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), nullable=False)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"), nullable=False)
    taille_id: Mapped[int | None] = mapped_column(ForeignKey("produit_tailles.id"))
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix_unitaire: Mapped[float] = mapped_column(Float, nullable=False)
    type_pate: Mapped[TypePate | None] = mapped_column(Enum(TypePate))
    moitie_moitie: Mapped[bool] = mapped_column(Boolean, default=False)
    moitie_produit_id: Mapped[int | None] = mapped_column(ForeignKey("produits.id"))
    notes: Mapped[str | None] = mapped_column(Text)

    commande: Mapped["Commande"] = relationship(back_populates="lignes")
    produit = relationship("Produit", foreign_keys=[produit_id], lazy="selectin")
    taille = relationship("ProduitTaille", lazy="selectin")
    moitie_produit = relationship("Produit", foreign_keys=[moitie_produit_id], lazy="selectin")
    supplements: Mapped[list["LigneCommandeSupplement"]] = relationship(
        back_populates="ligne", lazy="selectin", cascade="all, delete-orphan"
    )


class LigneCommandeSupplement(Base):
    __tablename__ = "lignes_commande_supplements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ligne_id: Mapped[int] = mapped_column(ForeignKey("lignes_commande.id", ondelete="CASCADE"), nullable=False)
    supplement_id: Mapped[int] = mapped_column(ForeignKey("supplements.id"), nullable=False)
    quantite: Mapped[int] = mapped_column(Integer, default=1)
    prix: Mapped[float] = mapped_column(Float, nullable=False)

    ligne: Mapped["LigneCommande"] = relationship(back_populates="supplements")
    supplement = relationship("Supplement", lazy="selectin")


class Paiement(Base, TimestampMixin):
    __tablename__ = "paiements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commande_id: Mapped[int] = mapped_column(ForeignKey("commandes.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[ModePaiement] = mapped_column(Enum(ModePaiement), nullable=False)
    montant: Mapped[float] = mapped_column(Float, nullable=False)
    rendu_monnaie: Mapped[float] = mapped_column(Float, default=0.0)

    commande: Mapped["Commande"] = relationship(back_populates="paiements")
