# medisecure-backend/api/controllers/auth_controller.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
import os
import logging
from dotenv import load_dotenv
import bcrypt

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
        
        # Récupérer le container et l'authentificateur
        container = get_container()
        authenticator = container.authenticator()
        
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
            # Générer un nouveau hash pour comparaison
            temp_hash = bcrypt.hashpw(form_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            logger.debug(f"Hash temporaire généré pour Admin123!: {temp_hash}")
            
            # Vérifier avec bcrypt directement
            try:
                is_password_valid = bcrypt.checkpw(
                    form_data.password.encode('utf-8'), 
                    user_model.hashed_password.encode('utf-8')
                )
            except Exception as e:
                logger.error(f"Erreur bcrypt: {e}")
                # En cas d'erreur, utiliser l'authentificateur
                is_password_valid = authenticator.verify_password(form_data.password, user_model.hashed_password)
        else:
            # Pour les autres mots de passe, utiliser l'authentificateur
            is_password_valid = authenticator.verify_password(form_data.password, user_model.hashed_password)
        
        if not is_password_valid:
            logger.warning(f"Mot de passe invalide pour: {user_model.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"Authentification réussie pour: {user_model.email}")
        
        # Récupérer le rôle sous forme de chaîne
        role_str = user_model.role.value if hasattr(user_model.role, 'value') else str(user_model.role)
        
        # Données du token
        token_data = {
            "sub": str(user_model.id),
            "email": user_model.email,
            "role": role_str,
            "name": f"{user_model.first_name} {user_model.last_name}"
        }
        
        # Créer le token avec une durée d'expiration
        access_token_expires = timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
        access_token = authenticator.create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        # Créer la réponse
        response = TokenResponseDTO(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")) * 60,
            user={
                "id": str(user_model.id),
                "email": user_model.email,
                "first_name": user_model.first_name,
                "last_name": user_model.last_name,
                "role": role_str,
                "is_active": user_model.is_active,
                "created_at": user_model.created_at.isoformat() if user_model.created_at else None,
                "updated_at": user_model.updated_at.isoformat() if user_model.updated_at else None
            }
        )
        
        logger.info("Token JWT généré avec succès")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de l'authentification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur est survenue lors de l'authentification",
        )

@router.post("/logout")
async def logout():
    """
    Route de déconnexion.
    
    Returns:
        dict: Message de confirmation
    """
    # La déconnexion est gérée côté client en supprimant le token
    return {"detail": "Déconnexion réussie"}

@router.get("/verify")
async def verify_token(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(lambda: {})  # Remplacer par votre extraction de token
):
    """
    Vérifie la validité du token actuel.
    
    Returns:
        dict: Informations sur la validité du token
    """
    return {
        "valid": True,
        "user_id": token_payload.get("sub"),
        "email": token_payload.get("email"),
        "role": token_payload.get("role")
    }

# Endpoint de test pour générer un hash de mot de passe
@router.post("/test-hash", include_in_schema=False)
async def test_hash(password: str):
    """
    Endpoint de test pour générer un hash de mot de passe.
    À utiliser uniquement en développement.
    """
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cet endpoint n'est disponible qu'en développement"
        )
    
    container = get_container()
    authenticator = container.authenticator()
    
    # Générer le hash avec l'authentificateur
    hash_from_auth = authenticator.get_password_hash(password)
    
    # Générer le hash avec bcrypt directement
    hash_from_bcrypt = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Vérifier avec les deux méthodes
    verify_auth = authenticator.verify_password(password, hash_from_auth)
    verify_bcrypt = bcrypt.checkpw(password.encode('utf-8'), hash_from_bcrypt.encode('utf-8'))
    
    return {
        "password": password,
        "hash_from_authenticator": hash_from_auth,
        "hash_from_bcrypt": hash_from_bcrypt,
        "verify_with_authenticator": verify_auth,
        "verify_with_bcrypt": verify_bcrypt
    }