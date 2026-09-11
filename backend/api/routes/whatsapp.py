"""Routes pour le webhook WhatsApp Business API."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.services import whatsapp_service

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


@router.get("/webhook")
async def verify_webhook(
    mode: str | None = None,
    token: str | None = None,
    challenge: str | None = None,
):
    """Verification du webhook par Meta (appele une seule fois)."""
    # Les params arrivent via hub.mode, hub.verify_token, hub.challenge
    # FastAPI les renomme via alias ou on les passe en query
    if mode == "subscribe" and token == whatsapp_service.VERIFY_TOKEN:
        return Response(content=challenge or "", media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Reception des messages WhatsApp entrants."""
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not whatsapp_service.verify_signature(body, signature):
        return Response(content="Invalid signature", status_code=401)

    data = await request.json()
    await whatsapp_service.handle_message(db, data)

    # Toujours retourner 200 pour que Meta ne renvoie pas le message
    return {"status": "ok"}
