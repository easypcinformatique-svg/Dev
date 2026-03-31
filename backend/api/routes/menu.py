"""Routes pour la gestion du menu (pizzas, categories, supplements, formules)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/menu", tags=["menu"])
