"""Tests des correctifs de securite (seed, login, numero de commande)."""

import asyncio
import re

import httpx
import pytest

from backend.api.routes import auth as auth_routes
from backend.db.database import get_db
from backend.main import app
from backend.services import auth_service, commande_service


def _requete(methode, url, **kw):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.request(methode, url, **kw)
    return asyncio.run(go())


def test_seed_force_exige_un_admin():
    assert _requete("POST", "/api/seed?force=true").status_code == 403
    jeton = auth_service.create_access_token(1, "caissier")
    r = _requete("POST", "/api/seed?force=true", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 403


def test_seed_force_accepte_un_admin():
    jeton = auth_service.create_access_token(1, "admin")
    r = _requete("POST", "/api/seed?force=true", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code != 403


def test_login_limite_les_tentatives(monkeypatch):
    async def faux_db():
        yield None

    async def refuse(db, pin):
        return None

    app.dependency_overrides[get_db] = faux_db
    monkeypatch.setattr(auth_service, "authenticate", refuse)
    auth_routes._echecs.clear()
    try:
        codes = [_requete("POST", "/api/auth/login", json={"pin": "0000"}).status_code for _ in range(7)]
    finally:
        app.dependency_overrides.clear()
        auth_routes._echecs.clear()
    assert codes[:5] == [401] * 5
    assert codes[5:] == [429, 429]


def test_numero_commande_format_et_diversite():
    numeros = {commande_service._generer_numero() for _ in range(2000)}
    assert all(re.fullmatch(r"P-[A-Z0-9]{6}", n) for n in numeros)
    assert len(numeros) == 2000
