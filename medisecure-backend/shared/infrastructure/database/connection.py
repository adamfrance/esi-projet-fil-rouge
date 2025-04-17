# medisecure-backend/shared/infrastructure/database/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

load_dotenv()

# Récupération de l'URL de connexion à la base de données
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/medisecure")

# S'assurer que nous utilisons bien asyncpg
if "postgresql://" in DATABASE_URL and "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

logger.info(f"Utilisation de l'URL de base de données: {DATABASE_URL.split('@')[0].split(':')[0]}:***@{DATABASE_URL.split('@')[1]}")

# Créer le moteur de base de données asynchrone
engine = create_async_engine(DATABASE_URL, echo=True)

# Création de la session asynchrone
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Classe de base pour les modèles
Base = declarative_base()

async def get_db():
    """Fournit une session de base de données asynchrone pour les opérations"""
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()