"""Service WhatsApp Business API - reception et envoi de messages."""

import hashlib
import hmac
import json
import os
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import ConversationWA, EtapeWhatsApp
from backend.services import commande_service, creneau_service, menu_service

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")

API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verifie la signature HMAC-SHA256 du webhook Meta."""
    if not APP_SECRET:
        return True  # Mode dev
    expected = "sha256=" + hmac.new(
        APP_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def send_message(to: str, text: str):
    """Envoie un message texte simple."""
    if not ACCESS_TOKEN:
        return  # Mode dev
    async with httpx.AsyncClient() as client:
        await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
        )


async def send_list_message(to: str, header: str, body: str, sections: list[dict]):
    """Envoie un message avec une liste interactive (menu)."""
    if not ACCESS_TOKEN:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header},
                    "body": {"text": body},
                    "action": {"button": "Voir le menu", "sections": sections},
                },
            },
        )


async def send_buttons(to: str, text: str, buttons: list[dict]):
    """Envoie un message avec des boutons (max 3)."""
    if not ACCESS_TOKEN:
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                            for b in buttons[:3]
                        ]
                    },
                },
            },
        )


async def get_or_create_conversation(
    db: AsyncSession, telephone: str
) -> ConversationWA:
    result = await db.execute(
        select(ConversationWA).where(ConversationWA.telephone == telephone)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = ConversationWA(telephone=telephone, etape=EtapeWhatsApp.ACCUEIL)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv


async def handle_message(db: AsyncSession, webhook_data: dict):
    """Traite un message entrant WhatsApp."""
    try:
        entry = webhook_data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return

        message = value["messages"][0]
        phone = message["from"]
        msg_type = message["type"]

        conv = await get_or_create_conversation(db, phone)

        # Extraire le contenu du message
        text = ""
        button_id = ""
        list_id = ""

        if msg_type == "text":
            text = message["text"]["body"].strip().lower()
        elif msg_type == "interactive":
            interactive = message["interactive"]
            if interactive["type"] == "button_reply":
                button_id = interactive["button_reply"]["id"]
            elif interactive["type"] == "list_reply":
                list_id = interactive["list_reply"]["id"]

        # Machine a etats
        if conv.etape == EtapeWhatsApp.ACCUEIL or text in ("menu", "commander", "bonjour", "salut"):
            await _envoyer_menu(db, phone)
            conv.etape = EtapeWhatsApp.MENU
            conv.panier_json = "[]"

        elif conv.etape == EtapeWhatsApp.MENU:
            if list_id or text:
                produit_id = list_id or text
                panier = json.loads(conv.panier_json or "[]")
                panier.append({"produit_id": produit_id, "taille": None, "supplements": []})
                conv.panier_json = json.dumps(panier)
                conv.etape = EtapeWhatsApp.TAILLE
                await send_buttons(phone, "Quelle taille ?", [
                    {"id": "junior", "title": "Junior"},
                    {"id": "medium", "title": "Medium"},
                    {"id": "large", "title": "Large"},
                ])

        elif conv.etape == EtapeWhatsApp.TAILLE:
            taille = button_id or text
            panier = json.loads(conv.panier_json or "[]")
            if panier:
                panier[-1]["taille"] = taille
            conv.panier_json = json.dumps(panier)
            conv.etape = EtapeWhatsApp.MODE
            await send_buttons(phone, "Autre pizza ou finaliser ?", [
                {"id": "ajouter", "title": "Ajouter une pizza"},
                {"id": "finaliser", "title": "Finaliser"},
            ])

        elif conv.etape == EtapeWhatsApp.MODE:
            if button_id == "ajouter" or text == "ajouter":
                await _envoyer_menu(db, phone)
                conv.etape = EtapeWhatsApp.MENU
            else:
                await send_buttons(phone, "Mode de retrait ?", [
                    {"id": "emporter", "title": "A emporter"},
                    {"id": "livraison", "title": "Livraison"},
                ])
                conv.etape = EtapeWhatsApp.CRENEAU

        elif conv.etape == EtapeWhatsApp.CRENEAU:
            mode = button_id or text
            conv.mode = mode
            if mode == "livraison":
                await send_message(phone, "Envoyez-moi votre adresse de livraison :")
                conv.etape = EtapeWhatsApp.ADRESSE
            else:
                await _envoyer_recap(conv, phone)
                conv.etape = EtapeWhatsApp.RECAP

        elif conv.etape == EtapeWhatsApp.ADRESSE:
            conv.adresse = text or message.get("text", {}).get("body", "")
            await _envoyer_recap(conv, phone)
            conv.etape = EtapeWhatsApp.RECAP

        elif conv.etape == EtapeWhatsApp.RECAP:
            if button_id == "confirmer" or "oui" in text or "confirm" in text:
                await _creer_commande_wa(db, conv, phone)
                conv.etape = EtapeWhatsApp.ACCUEIL
                conv.panier_json = "[]"
            else:
                await send_message(phone, "Commande annulee. Envoyez 'menu' pour recommencer.")
                conv.etape = EtapeWhatsApp.ACCUEIL
                conv.panier_json = "[]"

        await db.commit()

    except Exception as e:
        # Log l'erreur mais ne pas crasher le webhook
        print(f"Erreur WhatsApp: {e}")


async def _envoyer_menu(db: AsyncSession, phone: str):
    """Envoie le menu sous forme de liste interactive."""
    categories = await menu_service.get_categories(db, actif_only=True)
    sections = []
    for cat in categories:
        rows = []
        for p in cat.produits[:10]:  # Max 10 items par section
            if p.actif and p.tailles:
                prix_min = min(t.prix for t in p.tailles)
                rows.append({
                    "id": str(p.id),
                    "title": p.nom[:24],
                    "description": f"A partir de {prix_min:.2f} EUR",
                })
        if rows:
            sections.append({"title": cat.nom[:24], "rows": rows})

    if sections:
        await send_list_message(
            phone,
            "Notre Carte",
            "Choisissez votre pizza :",
            sections,
        )
    else:
        await send_message(phone, "Desolee, le menu n'est pas disponible pour le moment.")


async def _envoyer_recap(conv: ConversationWA, phone: str):
    """Envoie le recapitulatif de la commande."""
    panier = json.loads(conv.panier_json or "[]")
    lines = ["Recapitulatif de votre commande :\n"]
    for i, item in enumerate(panier, 1):
        taille = item.get("taille", "medium")
        lines.append(f"{i}. Pizza #{item['produit_id']} - Taille {taille}")
    mode = "A emporter" if conv.mode == "emporter" else "En livraison"
    lines.append(f"\nMode : {mode}")
    if conv.adresse:
        lines.append(f"Adresse : {conv.adresse}")
    lines.append("\nConfirmer ?")

    await send_buttons(phone, "\n".join(lines), [
        {"id": "confirmer", "title": "Oui, confirmer"},
        {"id": "annuler", "title": "Annuler"},
    ])


async def _creer_commande_wa(db: AsyncSession, conv: ConversationWA, phone: str):
    """Cree la commande dans le POS depuis WhatsApp."""
    panier = json.loads(conv.panier_json or "[]")
    lignes = []
    for item in panier:
        lignes.append({
            "produit_id": int(item["produit_id"]),
            "taille_id": None,  # A resoudre selon la taille choisie
            "quantite": 1,
            "supplements": [],
        })

    mode = "livraison" if conv.mode == "livraison" else "emporter"
    data = {
        "comptoir": "whatsapp",
        "mode": mode,
        "client_telephone": phone,
        "client_nom": f"WhatsApp {phone[-4:]}",
        "adresse_livraison": conv.adresse,
        "lignes": lignes,
    }

    try:
        commande = await commande_service.creer_commande(db, data)
        await send_message(
            phone,
            f"Commande confirmee ! Numero : {commande.numero}\n"
            f"Total : {commande.montant_ttc:.2f} EUR\n"
            f"Nous vous prevenons quand c'est pret !",
        )
        # Broadcast vers la cuisine
        from backend.websocket.manager import broadcast_order_event
        await broadcast_order_event("new_order", {
            "id": commande.id,
            "numero": commande.numero,
            "comptoir": "whatsapp",
            "mode": mode,
        })
    except Exception as e:
        await send_message(phone, f"Erreur lors de la commande. Veuillez reessayer. ({e})")
