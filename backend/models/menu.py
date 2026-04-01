"""Modeles pour la gestion du menu (categories, produits, supplements, formules)."""

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin
from .enums import TaillePizza, TypePate


class Categorie(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    tva_taux: Mapped[float] = mapped_column(Float, default=10.0)
    image_url: Mapped[str | None] = mapped_column(String(500))

    produits: Mapped[list["Produit"]] = relationship(
        back_populates="categorie", lazy="selectin", order_by="Produit.ordre"
    )


class Produit(Base, TimestampMixin):
    __tablename__ = "produits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categorie_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    ordre: Mapped[int] = mapped_column(Integer, default=0)
    base_sauce: Mapped[str | None] = mapped_column(String(50))
    allergenes: Mapped[str | None] = mapped_column(Text)  # CSV: gluten,lactose,oeuf
    est_pizza: Mapped[bool] = mapped_column(Boolean, default=False)
    temps_preparation: Mapped[int] = mapped_column(Integer, default=10)  # minutes

    categorie: Mapped["Categorie"] = relationship(back_populates="produits")
    tailles: Mapped[list["ProduitTaille"]] = relationship(
        back_populates="produit", lazy="selectin"
    )
    ingredients_fiche: Mapped[list["ProduitIngredient"]] = relationship(
        back_populates="produit", lazy="selectin"
    )


class ProduitTaille(Base):
    __tablename__ = "produit_tailles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id", ondelete="CASCADE"), nullable=False)
    taille: Mapped[TaillePizza] = mapped_column(Enum(TaillePizza), nullable=False)
    prix: Mapped[float] = mapped_column(Float, nullable=False)

    produit: Mapped["Produit"] = relationship(back_populates="tailles")


class Supplement(Base, TimestampMixin):
    __tablename__ = "supplements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    prix: Mapped[float] = mapped_column(Float, nullable=False)
    categorie: Mapped[str | None] = mapped_column(String(100))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
    allergenes: Mapped[str | None] = mapped_column(Text)


class Formule(Base, TimestampMixin):
    __tablename__ = "formules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    prix: Mapped[float] = mapped_column(Float, nullable=False)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    elements: Mapped[list["FormuleElement"]] = relationship(
        back_populates="formule", lazy="selectin"
    )


class FormuleElement(Base):
    __tablename__ = "formule_elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    formule_id: Mapped[int] = mapped_column(ForeignKey("formules.id", ondelete="CASCADE"), nullable=False)
    categorie_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    nb_choix: Mapped[int] = mapped_column(Integer, default=1)

    formule: Mapped["Formule"] = relationship(back_populates="elements")
    categorie: Mapped["Categorie"] = relationship()


class ProduitIngredient(Base):
    """Fiche technique : lien produit <-> ingredient pour le stock."""
    __tablename__ = "produit_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id", ondelete="CASCADE"), nullable=False)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantite: Mapped[float] = mapped_column(Float, default=1.0)

    produit: Mapped["Produit"] = relationship(back_populates="ingredients_fiche")
    ingredient: Mapped["Ingredient"] = relationship()


class Ingredient(Base, TimestampMixin):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    unite: Mapped[str] = mapped_column(String(50), default="unite")
    quantite_stock: Mapped[float] = mapped_column(Float, default=0.0)
    seuil_alerte: Mapped[float] = mapped_column(Float, default=5.0)


class Promotion(Base, TimestampMixin):
    """Promotions et codes promo."""
    __tablename__ = "promotions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    nom: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type_promo: Mapped[str] = mapped_column(String(50), nullable=False)  # TypePromo value
    valeur: Mapped[float] = mapped_column(Float, nullable=False)  # % ou montant
    montant_min: Mapped[float] = mapped_column(Float, default=0.0)  # commande min
    max_utilisations: Mapped[int | None] = mapped_column(Integer)
    nb_utilisations: Mapped[int] = mapped_column(Integer, default=0)
    actif: Mapped[bool] = mapped_column(Boolean, default=True)
