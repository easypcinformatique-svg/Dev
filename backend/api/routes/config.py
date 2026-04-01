"""Routes pour la configuration de la pizzeria."""

import os

from fastapi import APIRouter, Depends

from backend.api.deps import require_admin

router = APIRouter(prefix="/api/config", tags=["configuration"])


@router.get("/pizzeria")
async def get_config():
    return {
        "nom": os.getenv("PIZZERIA_NOM", "Ma Pizzeria"),
        "telephone": os.getenv("PIZZERIA_TEL", ""),
        "adresse": os.getenv("PIZZERIA_ADRESSE", ""),
        "siret": os.getenv("PIZZERIA_SIRET", ""),
    }


@router.get("/comptoirs")
async def get_comptoirs():
    """Liste des comptoirs disponibles avec leurs couleurs."""
    return [
        {"id": "accueil", "nom": "Comptoir Accueil", "couleur": "#3B82F6", "icone": "store"},
        {"id": "web", "nom": "Comptoir Web", "couleur": "#10B981", "icone": "globe"},
        {"id": "whatsapp", "nom": "Comptoir WhatsApp", "couleur": "#8B5CF6", "icone": "message-circle"},
        {"id": "livraison_platform", "nom": "Plateformes Livraison", "couleur": "#F97316", "icone": "truck"},
    ]
