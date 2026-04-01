"""Schemas Pydantic pour la validation des requetes et reponses API."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field

from .enums import (
    Comptoir, ModeCommande, ModePaiement, Role, StatutCommande,
    StatutLivreur, StatutPaiement, TaillePizza, TypePate,
)


# ── Auth ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


class UtilisateurCreate(BaseModel):
    nom: str
    pin: str = Field(..., min_length=4, max_length=6)
    role: Role


class UtilisateurResponse(BaseModel):
    id: int
    nom: str
    role: Role
    actif: bool
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurResponse


# ── Menu ──────────────────────────────────────────────────────

class ProduitTailleResponse(BaseModel):
    id: int
    taille: TaillePizza
    prix: float
    model_config = {"from_attributes": True}


class ProduitResponse(BaseModel):
    id: int
    categorie_id: int
    nom: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    actif: bool
    base_sauce: Optional[str] = None
    allergenes: Optional[str] = None
    est_pizza: bool = False
    temps_preparation: int = 10
    tailles: list[ProduitTailleResponse] = []
    model_config = {"from_attributes": True}


class CategorieResponse(BaseModel):
    id: int
    nom: str
    description: Optional[str] = None
    ordre: int
    actif: bool
    tva_taux: float
    image_url: Optional[str] = None
    produits: list[ProduitResponse] = []
    model_config = {"from_attributes": True}


class CategorieCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    ordre: int = 0
    tva_taux: float = 10.0


class ProduitTailleCreate(BaseModel):
    taille: TaillePizza
    prix: float


class ProduitCreate(BaseModel):
    categorie_id: int
    nom: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_sauce: Optional[str] = None
    allergenes: Optional[str] = None
    est_pizza: bool = False
    temps_preparation: int = 10
    tailles: list[ProduitTailleCreate] = []


class ProduitUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_sauce: Optional[str] = None
    actif: Optional[bool] = None
    categorie_id: Optional[int] = None
    allergenes: Optional[str] = None
    est_pizza: Optional[bool] = None
    temps_preparation: Optional[int] = None


class SupplementCreate(BaseModel):
    nom: str
    prix: float
    categorie: Optional[str] = None
    allergenes: Optional[str] = None


class SupplementResponse(BaseModel):
    id: int
    nom: str
    prix: float
    categorie: Optional[str] = None
    actif: bool
    allergenes: Optional[str] = None
    model_config = {"from_attributes": True}


class FormuleElementCreate(BaseModel):
    categorie_id: int
    nb_choix: int = 1


class FormuleCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    prix: float
    elements: list[FormuleElementCreate] = []


class FormuleElementResponse(BaseModel):
    id: int
    categorie_id: int
    nb_choix: int
    model_config = {"from_attributes": True}


class FormuleResponse(BaseModel):
    id: int
    nom: str
    description: Optional[str] = None
    prix: float
    actif: bool
    elements: list[FormuleElementResponse] = []
    model_config = {"from_attributes": True}


# ── Clients ───────────────────────────────────────────────────

class ClientCreate(BaseModel):
    nom: str
    telephone: str
    email: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    id: int
    nom: str
    telephone: str
    email: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    notes: Optional[str] = None
    points_fidelite: int = 0
    nb_commandes: int = 0
    model_config = {"from_attributes": True}


# ── Creneaux ──────────────────────────────────────────────────

class CreneauConfigCreate(BaseModel):
    jour_semaine: int = Field(..., ge=0, le=6)
    heure_debut: time
    heure_fin: time
    intervalle_minutes: int = 15
    capacite_max: int = 10


class CreneauConfigResponse(BaseModel):
    id: int
    jour_semaine: int
    heure_debut: time
    heure_fin: time
    intervalle_minutes: int
    capacite_max: int
    actif: bool
    model_config = {"from_attributes": True}


class CreneauResponse(BaseModel):
    id: int
    date: date
    heure_debut: time
    heure_fin: time
    capacite_max: int
    nb_commandes: int
    verrouille: bool
    disponible: bool
    label: str
    model_config = {"from_attributes": True}


# ── Commandes ─────────────────────────────────────────────────

class LigneSupplementCreate(BaseModel):
    supplement_id: int
    quantite: int = 1


class LigneCommandeCreate(BaseModel):
    produit_id: int
    taille_id: Optional[int] = None
    quantite: int = 1
    type_pate: Optional[TypePate] = None
    moitie_moitie: bool = False
    moitie_produit_id: Optional[int] = None
    notes: Optional[str] = None
    supplements: list[LigneSupplementCreate] = []


class CommandeCreate(BaseModel):
    comptoir: Comptoir = Comptoir.ACCUEIL
    mode: ModeCommande
    client_id: Optional[int] = None
    client_telephone: Optional[str] = None
    client_nom: Optional[str] = None
    creneau_id: Optional[int] = None
    adresse_livraison: Optional[str] = None
    code_promo: Optional[str] = None
    notes: Optional[str] = None
    lignes: list[LigneCommandeCreate]


class LigneSupplementResponse(BaseModel):
    id: int
    supplement_id: int
    quantite: int
    prix: float
    model_config = {"from_attributes": True}


class LigneCommandeResponse(BaseModel):
    id: int
    produit_id: int
    taille_id: Optional[int] = None
    quantite: int
    prix_unitaire: float
    type_pate: Optional[TypePate] = None
    moitie_moitie: bool = False
    moitie_produit_id: Optional[int] = None
    notes: Optional[str] = None
    supplements: list[LigneSupplementResponse] = []
    # Champs enrichis depuis les relations
    produit: Optional[ProduitResponse] = None
    taille: Optional[ProduitTailleResponse] = None
    moitie_produit: Optional[ProduitResponse] = None
    model_config = {"from_attributes": True}


class CommandeResponse(BaseModel):
    id: int
    numero: str
    comptoir: Comptoir
    mode: ModeCommande
    statut: StatutCommande
    client: Optional[ClientResponse] = None
    creneau: Optional[CreneauResponse] = None
    montant_ht: float
    montant_tva: float
    montant_ttc: float
    frais_livraison: float
    remise: float
    code_promo: Optional[str] = None
    adresse_livraison: Optional[str] = None
    mode_paiement: Optional[ModePaiement] = None
    statut_paiement: StatutPaiement
    temps_estime: Optional[int] = None
    notes: Optional[str] = None
    lignes: list[LigneCommandeResponse] = []
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class CommandeStatusUpdate(BaseModel):
    statut: StatutCommande


# ── Caisse ────────────────────────────────────────────────────

class PaiementItem(BaseModel):
    mode: ModePaiement
    montant: float


class EncaissementRequest(BaseModel):
    commande_id: int
    paiements: list[PaiementItem]
    montant_recu_especes: Optional[float] = None


class TicketZResponse(BaseModel):
    date: date
    nb_commandes: int
    ca_ttc: float
    ca_ht: float
    total_tva: float
    par_comptoir: dict[str, float]
    par_mode_paiement: dict[str, float]
    par_mode: dict[str, float]
    fond_de_caisse: float
    total_especes: float
    total_cb: float


# ── Livraisons ────────────────────────────────────────────────

class LivreurCreate(BaseModel):
    nom: str
    telephone: str


class LivreurResponse(BaseModel):
    id: int
    nom: str
    telephone: str
    statut: StatutLivreur
    actif: bool
    model_config = {"from_attributes": True}


class ZoneLivraisonCreate(BaseModel):
    nom: str
    codes_postaux: list[str] = []
    rayon_km: Optional[float] = None
    frais_livraison: float = 0.0


class ZoneLivraisonResponse(BaseModel):
    id: int
    nom: str
    codes_postaux: Optional[list[str]] = None
    rayon_km: Optional[float] = None
    frais_livraison: float
    actif: bool
    model_config = {"from_attributes": True}


class AssignerLivreurRequest(BaseModel):
    commande_id: int
    livreur_id: int


# ── Promotions ────────────────────────────────────────────────

class PromoCheckRequest(BaseModel):
    code: str
    montant: float


class PromoCheckResponse(BaseModel):
    valide: bool
    remise: float = 0
    message: str = ""
