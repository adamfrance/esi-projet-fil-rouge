# medisecure-backend/shared/container/container.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv

from shared.adapters.primary.uuid_generator import UuidGenerator
from shared.adapters.secondary.postgres_user_repository import PostgresUserRepository
from shared.adapters.secondary.in_memory_user_repository import InMemoryUserRepository
from shared.infrastructure.services.smtp_mailer import SmtpMailer
from shared.services.authenticator.basic_authenticator import BasicAuthenticator

from patient_management.infrastructure.adapters.secondary.postgres_patient_repository import PostgresPatientRepository
from patient_management.infrastructure.adapters.secondary.in_memory_patient_repository import InMemoryPatientRepository
from patient_management.domain.services.patient_service import PatientService

from appointment_management.infrastructure.adapters.secondary.postgres_appointment_repository import PostgresAppointmentRepository
from appointment_management.infrastructure.adapters.secondary.in_memory_appointment_repository import InMemoryAppointmentRepository
from appointment_management.domain.services.appointment_service import AppointmentService

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Container(containers.DeclarativeContainer):
    """
    Container d'injection de dépendances pour l'application.
    Centralise la création et la gestion des instances des différentes classes.
    """
    
    config = providers.Configuration()
    
    # Configuration du container
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/medisecure")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # S'assurer que nous utilisons bien asyncpg
    if "postgresql://" in database_url and "asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Vérifier si nous sommes en mode Docker
    if os.getenv("ENVIRONMENT") == "docker" or os.path.exists("/.dockerenv"):
        # En mode Docker, utiliser l'hôte 'db'
        database_url = database_url.replace("@localhost:", "@db:")
    
    config.database_url.from_value(database_url)
    config.environment.from_value(environment)
    
    logger.info(f"Database URL configurée: {database_url.split('@')[0]}:***@{database_url.split('@')[1] if '@' in database_url else 'N/A'}")
    
    # Création du moteur avec les bonnes options
    engine = providers.Singleton(
        create_async_engine,
        database_url,
        echo=True if environment == "development" else False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Vérifier la connexion avant de l'utiliser
        pool_recycle=3600,   # Recycler les connexions toutes les heures
    )
    
    # Création de la factory de session
    async_session_factory = providers.Singleton(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False
    )
    
    # Gestionnaire de contexte pour les sessions
    @asynccontextmanager
    async def get_session():
        async_session = async_session_factory()
        async with async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    
    # Adaptateurs primaires
    id_generator = providers.Factory(UuidGenerator)
    authenticator = providers.Factory(BasicAuthenticator)
    
    # Services du domaine
    patient_service = providers.Factory(PatientService)
    appointment_service = providers.Factory(AppointmentService)
    
    # Adaptateurs secondaires - Repositories

    # Pour production :
    user_repository = providers.Factory(
        PostgresUserRepository,
        session=async_session_factory
    )

    patient_repository = providers.Factory(
        PostgresPatientRepository,
        session=async_session_factory
    )

    appointment_repository = providers.Factory(
        PostgresAppointmentRepository,
        session=async_session_factory
    )
    
    # Repositories en mémoire pour les tests
    user_repository_in_memory = providers.Singleton(InMemoryUserRepository)
    patient_repository_in_memory = providers.Singleton(InMemoryPatientRepository)
    appointment_repository_in_memory = providers.Singleton(InMemoryAppointmentRepository)
    
    # Services d'infrastructure
    mailer = providers.Factory(SmtpMailer)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Container d'injection de dépendances initialisé")
        logger.info(f"Environnement: {self.config.environment}")
        logger.info(f"Mode: {'Docker' if os.getenv('ENVIRONMENT') == 'docker' or os.path.exists('/.dockerenv') else 'Local'}")

# Instance globale du container pour faciliter l'accès
container_instance = None

def get_container():
    """
    Retourne l'instance globale du container.
    Crée une nouvelle instance si elle n'existe pas.
    """
    global container_instance
    if container_instance is None:
        container_instance = Container()
    return container_instance

# Pour les tests
def reset_container():
    """
    Réinitialise le container (utile pour les tests).
    """
    global container_instance
    if container_instance:
        container_instance.shutdown_resources()
    container_instance = None