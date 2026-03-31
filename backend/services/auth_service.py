"""Service d'authentification par code PIN."""

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Utilisateur, Role

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 12

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    return pwd_context.verify(plain_pin, hashed_pin)


def create_access_token(utilisateur_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": str(utilisateur_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def authenticate(db: AsyncSession, pin: str) -> Utilisateur | None:
    result = await db.execute(
        select(Utilisateur).where(Utilisateur.actif.is_(True))
    )
    utilisateurs = result.scalars().all()
    for u in utilisateurs:
        if verify_pin(pin, u.pin_hash):
            return u
    return None


async def create_utilisateur(
    db: AsyncSession, nom: str, pin: str, role: Role
) -> Utilisateur:
    utilisateur = Utilisateur(
        nom=nom,
        pin_hash=hash_pin(pin),
        role=role,
    )
    db.add(utilisateur)
    await db.commit()
    await db.refresh(utilisateur)
    return utilisateur


async def get_utilisateur(db: AsyncSession, utilisateur_id: int) -> Utilisateur | None:
    result = await db.execute(
        select(Utilisateur).where(Utilisateur.id == utilisateur_id)
    )
    return result.scalar_one_or_none()
