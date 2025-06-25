# medisecure-backend/api/middlewares/authentication_middleware.py

from fastapi import Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional, Dict, Any
import os
from datetime import datetime
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

security = HTTPBearer()

class AuthenticationMiddleware:
    """Middleware pour vérifier l'authentification JWT"""
    
    def __init__(self):
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "default_secret_key")
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
    async def __call__(self, request: Request, call_next):
        """Vérifie le token JWT et ajoute l'utilisateur à la requête"""
        
        # Chemins exemptés d'authentification
        exempt_paths = [
            "/api/health", 
            "/api/docs", 
            "/api/redoc", 
            "/api/openapi.json", 
            "/api/auth/login", 
            "/api/auth/logout",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/"
        ]
        
        # Méthode OPTIONS pour les requêtes CORS preflight - TOUJOURS autoriser
        if request.method == "OPTIONS":
            response = Response()
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            return response
            
        # Vérifier si le chemin est exempté
        request_path = str(request.url.path)
        if any(request_path.startswith(path) for path in exempt_paths):
            logger.debug(f"Chemin exempté: {request_path}")
            return await call_next(request)
        
        # Récupérer le token d'autorisation
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.info(f"Pas de token d'autorisation pour: {request_path}")
            # Pour les autres endpoints, continuer sans authentification pour le moment
            return await call_next(request)
        
        try:
            # Extraction du token
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                logger.warning(f"Schéma d'autorisation invalide: {scheme}")
                return await call_next(request)
                
            # Validation du token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.algorithm])
            
            # Vérification de l'expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
                logger.warning(f"Token expiré pour: {request_path}")
                return await call_next(request)
            
            # Ajout de l'utilisateur à la requête
            request.state.user = payload
            logger.debug(f"Utilisateur authentifié: {payload.get('email')} accède à {request_path}")
            
            return await call_next(request)
            
        except JWTError as e:
            logger.warning(f"Erreur JWT pour {request_path}: {str(e)}")
            return await call_next(request)
        except ValueError as e:
            logger.warning(f"Erreur de format du token pour {request_path}: {str(e)}")
            return await call_next(request)
        except Exception as e:
            logger.error(f"Erreur d'authentification pour {request_path}: {str(e)}")
            return await call_next(request)