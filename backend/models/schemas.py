"""Schemas Pydantic pour la validation des requetes et reponses API."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field

from .enums import (
    Comptoir, ModeCommande, ModePaiement, Role, StatutCommande,
    StatutLivreur, StatutPaiement, TaillePizza,
)


# ── Auth ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurResponse


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


# ── Menu ──────────────────────────────────────────────────────

class CategorieCreate(BaseModel):
    nom: str
    description: Optional[str] = None
    ordre: int = 0
    tva_taux: float = 10.0
    image_url: Optional[str] = None


class CategorieResponse(BaseModel):
    id: int
    nom: str
    description: Optional[str]
    ordre: int
    actif: bool
    tva_taux: float
    image_url: Optional[str]
    produits: list[ProduitResponse] = []

    model_config = {"from_attributes": True}


class CategorieListResponse(BaseModel):
    id: int
    nom: str
    ordre: int
    actif: bool
    tva_taux: float

    model_config = {"from_attributes": True}


class ProduitTailleCreate(BaseModel):
    taille: TaillePizza
    prix: float


class ProduitTailleResponse(BaseModel):
    id: int
    taille: TaillePizza
    prix: float

    model_config = {"from_attributes": True}


class ProduitCreate(BaseModel):
    categorie_id: int
    nom: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_sauce: Optional[str] = None
    tailles: list[ProduitTailleCreate] = []


class ProduitUpdate(BaseModel):
    nom: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    base_sauce: Optional[str] = None
    actif: Optional[bool] = None
    categorie_id: Optional[int] = None


class ProduitResponse(BaseModel):
    id: int
    categorie_id: int
    nom: str
    description: Optional[str]
    image_url: Optional[str]
    actif: bool
    base_sauce: Optional[str]
    tailles: list[ProduitTailleResponse] = []

    model_config = {"from_attributes": True}


class SupplementCreate(BaseModel):
    nom: str
    prix: float
    categorie: Optional[str] = None


class SupplementResponse(BaseModel):
    id: int
    nom: str
    prix: float
    categorie: Optional[str]
    actif: bool

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
    description: Optional[str]
    prix: float
    actif: bool
    elements: list[FormuleElementResponse] = []

    model_config = {"from_attributes": True}


# ── Clients ───────────────────────────────────────────────────

class ClientCreate(BaseModel):
    nom: str
    telephone: str
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    id: int
    nom: str
    telephone: str
    adresse: Optional[str]
    code_postal: Optional[str]
    ville: Optional[str]
    notes: Optional[str]

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
    notes: Optional[str] = None
    lignes: list[LigneCommandeCreate]


class LigneSupplementResponse(BaseModel):
    id: int
    supplement_id: int
    supplement_nom: str = ""
    quantite: int
    prix: float

    model_config = {"from_attributes": True}


class LigneCommandeResponse(BaseModel):
    id: int
    produit_id: int
    produit_nom: str = ""
    taille: Optional[TaillePizza] = None
    quantite: int
    prix_unitaire: float
    notes: Optional[str]
    supplements: list[LigneSupplementResponse] = []

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
    adresse_livraison: Optional[str]
    mode_paiement: Optional[ModePaiement]
    statut_paiement: StatutPaiement
    notes: Optional[str]
    lignes: list[LigneCommandeResponse] = []
    created_at: datetime

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


class OuvertureCaisseRequest(BaseModel):
    fond_de_caisse: float


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
    codes_postaux: Optional[list[str]]
    rayon_km: Optional[float]
    frais_livraison: float
    actif: bool

    model_config = {"from_attributes": True}


class AssignerLivreurRequest(BaseModel):
    commande_id: int
    livreur_id: int


# ── Stats ─────────────────────────────────────────────────────

class StatJour(BaseModel):
    date: date
    nb_commandes: int
    ca_ttc: float
    panier_moyen: float


class TopProduit(BaseModel):
    produit_nom: str
    quantite_vendue: int
    ca_ttc: float


class StatsResponse(BaseModel):
    periode: str
    ca_ttc: float
    ca_ht: float
    nb_commandes: int
    panier_moyen: float
    par_comptoir: dict[str, dict]
    par_mode: dict[str, dict]
    top_produits: list[TopProduit]
    par_jour: list[StatJour]
    par_creneau: dict[str, int]


# ── Config ────────────────────────────────────────────────────

class PizzeriaConfig(BaseModel):
    nom: str = ""
    telephone: str = ""
    adresse: str = ""
    siret: str = ""
    tva_emporter: float = 10.0
    tva_livraison: float = 10.0
    logo_url: Optional[str] = None


# Resoudre les references forward
CategorieResponse.model_rebuild()
TokenResponse.model_rebuild()
