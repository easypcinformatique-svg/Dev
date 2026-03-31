"""Routes pour l'encaissement (paiements, ticket Z, ouverture/fermeture caisse)."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/caisse", tags=["caisse"])
