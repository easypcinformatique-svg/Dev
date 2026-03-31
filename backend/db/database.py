"""Configuration de la connexion a la base de donnees PostgreSQL."""

import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://pizzacaisse:changeme@localhost:5432/pizzacaisse",
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency FastAPI pour obtenir une session DB."""
    async with async_session() as session:
        yield session
