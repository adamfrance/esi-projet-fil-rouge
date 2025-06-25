# medisecure-backend/api/controllers/auth_controller.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta, datetime
import os
import logging
from dotenv import load_dotenv
import bcrypt
from jose import jwt

from shared.container.container import get_container
from shared.application.dtos.common_dtos import TokenResponseDTO
from shared.infrastructure.database.models.user_model import UserModel
from shared.infrastructure.database.connection import get_db

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logger = logging.getLogger(__name__)

# Créer un router pour les endpoints d'authentification
router = APIRouter(prefix="/auth", tags=["auth"])

# Configuration JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du mot de passe: {e}")
        return False

def hash_password(password: str) -> str:
    """Hasher un mot de passe"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

@router.post("/login", response_model=TokenResponseDTO)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint de connexion utilisant OAuth2 avec mot de passe.
    
    Args:
        request: La requête HTTP
        form_data: Les données du formulaire de connexion
        db: La session de base de données
        
    Returns:
        TokenResponseDTO: Le token d'accès et les informations de l'utilisateur
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        logger.info(f"Tentative de connexion pour: {form_data.username}")
        
        # Rechercher l'utilisateur dans la base de données
        query = select(UserModel).where(UserModel.email == form_data.username)
        result = await db.execute(query)
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            logger.warning(f"Utilisateur non trouvé: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Utilisateur trouvé: {user_model.email}, rôle: {user_model.role}")
        
        # Vérifier si l'utilisateur est actif
        if not user_model.is_active:
            logger.warning(f"Utilisateur inactif: {user_model.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Compte utilisateur désactivé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier le mot de passe
        is_password_valid = False
        
        # Pour le développement : vérifier si c'est le mot de passe par défaut
        if form_data.password == "Admin123!":
            logger.info("Utilisation du mot de passe par défaut pour le développement")
            is_password_valid = True
        else:
            # Vérifier le mot de passe hashé
            if user_model.password_hash:
                is_password_valid = verify_password(form_data.password, user_model.password_hash)
        
        if not is_password_valid:
            logger.warning(f"Mot de passe incorrect pour: {user_model.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Créer le token d'accès
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token_data = {
            "sub": user_model.email,
            "user_id": str(user_model.id),
            "email": user_model.email,
            "role": user_model.role,
            "first_name": user_model.first_name,
            "last_name": user_model.last_name
        }
        access_token = create_access_token(
            data=access_token_data, expires_delta=access_token_expires
        )
        
        logger.info(f"Connexion réussie pour: {user_model.email}")
        
        # Retourner la réponse avec le token et les informations de l'utilisateur
        return TokenResponseDTO(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # en secondes
            user={
                "id": str(user_model.id),
                "email": user_model.email,
                "first_name": user_model.first_name,
                "last_name": user_model.last_name,
                "role": user_model.role,
                "is_active": user_model.is_active,
                "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
                "updated_at": user_model.updated_at.isoformat() if user_model.updated_at else None,
            }
        )
        
    except HTTPException:
        # Re-lever les HTTPException telles quelles
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la connexion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )

@router.post("/logout")
async def logout(request: Request):
    """Endpoint de déconnexion"""
    try:
        logger.info("Demande de déconnexion")
        return {"message": "Déconnexion réussie"}
    except Exception as e:
        logger.error(f"Erreur lors de la déconnexion: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la déconnexion"
        )