"""Gestionnaire WebSocket pour les notifications temps reel (cuisine, suivi)."""

import json

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Gere les connexions WebSocket actives."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Envoie un message a toutes les connexions actives."""
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)


manager = ConnectionManager()


async def broadcast_order_event(event_type: str, data: dict):
    """Broadcast un evenement commande a tous les ecrans connectes."""
    await manager.broadcast({"event": event_type, "data": data})


async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket pour l'ecran cuisine et le suivi."""
    await manager.connect(websocket)
    try:
        while True:
            # Garder la connexion ouverte, recevoir les pings
            data = await websocket.receive_text()
            # On pourrait gerer des commandes du client WS ici
            if data == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
