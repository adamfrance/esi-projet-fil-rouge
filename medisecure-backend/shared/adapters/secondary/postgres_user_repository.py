from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from shared.domain.entities.user import User
from shared.domain.enums.roles import UserRole
from shared.infrastructure.database.models.user_model import UserModel
from shared.ports.secondary.user_repository_protocol import UserRepositoryProtocol

class PostgresUserRepository(UserRepositoryProtocol):
    """
    Adaptateur secondaire pour le repository des utilisateurs avec PostgreSQL.
    Implémente le port UserRepositoryProtocol.
    """
    
    def __init__(self, session_factory):
        """
        Initialise le repository avec une factory de session SQLAlchemy.
        
        Args:
            session_factory: La factory de session SQLAlchemy à utiliser
        """
        self.session_factory = session_factory
    
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        async with self.session_factory() as session:
            query = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(query)
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            return self._map_to_entity(user_model)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Récupère un utilisateur par son email.
        
        Args:
            email: L'email de l'utilisateur à récupérer
            
        Returns:
            Optional[User]: L'utilisateur trouvé ou None si non trouvé
        """
        async with self.session_factory() as session:
            query = select(UserModel).where(UserModel.email == email)
            result = await session.execute(query)
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            return self._map_to_entity(user_model)
    
    async def create(self, user: User) -> User:
        """
        Crée un nouvel utilisateur.
        
        Args:
            user: L'utilisateur à créer
            
        Returns:
            User: L'utilisateur créé avec son ID généré
        """
        async with self.session_factory() as session:
            user_model = UserModel(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            
            session.add(user_model)
            await session.commit()
            await session.refresh(user_model)
            
            return self._map_to_entity(user_model)
    
    async def update(self, user: User) -> User:
        """
        Met à jour un utilisateur existant.
        
        Args:
            user: L'utilisateur à mettre à jour
            
        Returns:
            User: L'utilisateur mis à jour
        """
        query = (
            update(UserModel)
            .where(UserModel.id == user.id)
            .values(
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                updated_at=user.updated_at
            )
        )
        
        await self.session.execute(query)
        await self.session.commit()
        
        return user
    
    async def delete(self, user_id: UUID) -> bool:
        """
        Supprime un utilisateur.
        
        Args:
            user_id: L'ID de l'utilisateur à supprimer
            
        Returns:
            bool: True si l'utilisateur a été supprimé, False sinon
        """
        query = delete(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(query)
        
        if result.rowcount == 0:
            return False
        
        await self.session.commit()
        return True
    
    async def list_all(self) -> List[User]:
        """
        Liste tous les utilisateurs.
        
        Returns:
            List[User]: La liste de tous les utilisateurs
        """
        query = select(UserModel)
        result = await self.session.execute(query)
        user_models = result.scalars().all()
        
        return [self._map_to_entity(user_model) for user_model in user_models]
    
    async def list_by_role(self, role: str) -> List[User]:
        """
        Liste les utilisateurs par rôle.
        
        Args:
            role: Le rôle des utilisateurs à lister
            
        Returns:
            List[User]: La liste des utilisateurs ayant le rôle spécifié
        """
        query = select(UserModel).where(UserModel.role == role)
        result = await self.session.execute(query)
        user_models = result.scalars().all()
        
        return [self._map_to_entity(user_model) for user_model in user_models]
    
    def _map_to_entity(self, user_model: UserModel) -> User:
        """
        Convertit un modèle SQLAlchemy en entité du domaine.
        
        Args:
            user_model: Le modèle SQLAlchemy à convertir
            
        Returns:
            User: L'entité du domaine correspondante
        """
        return User(
            id=user_model.id,
            email=user_model.email,
            first_name=user_model.first_name,
            last_name=user_model.last_name,
            role=UserRole(user_model.role.value),
            is_active=user_model.is_active,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at
        )
    
    async def get_hashed_password(self, user: User) -> str:
        """
        Récupère le mot de passe hashé d'un utilisateur.
        
        Args:
            user: L'utilisateur dont on veut récupérer le mot de passe hashé
            
        Returns:
            str: Le mot de passe hashé de l'utilisateur
        """
        query = select(UserModel.hashed_password).where(UserModel.id == user.id)
        result = await self.session.execute(query)
        hashed_password = result.scalar_one_or_none()
        
        return hashed_password
    
    def get_hashed_password(self, user):
        """
        Récupère le mot de passe hashé d'un utilisateur.
        
        Args:
            user: L'utilisateur dont on veut récupérer le mot de passe hashé
            
        Returns:
            str: Le mot de passe hashé de l'utilisateur
        """
        # Exécuter une requête pour récupérer le mot de passe hashé
        async def get_password():
            query = select(UserModel.hashed_password).where(UserModel.id == user.id)
            result = await self.session.execute(query)
            hashed_password = result.scalar_one_or_none()
            return hashed_password
        
        # Exécuter la tâche asynchrone de manière synchrone pour simplifier l'interface
        import asyncio
        loop = asyncio.get_event_loop()
        hashed_password = loop.run_until_complete(get_password())
        
        return hashed_password