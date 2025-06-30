# medisecure-backend/patient_management/infrastructure/adapters/primary/controllers/patient_controller.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from datetime import date
import logging

from shared.services.authenticator.extract_token import extract_token_payload
from shared.container.container import Container
from patient_management.application.dtos.patient_dtos import (
    PatientCreateDTO,
    PatientUpdateDTO,
    PatientResponseDTO,
    PatientListResponseDTO,
    PatientSearchDTO
)
from patient_management.application.usecases.create_patient_folder_usercase import CreatePatientFolderUseCase
from patient_management.application.usecases.update_patient_usecase import UpdatePatientUseCase
from patient_management.application.usecases.get_patient_usecase import GetPatientUseCase
from patient_management.domain.exceptions.patient_exceptions import (
    PatientNotFoundException,
    PatientAlreadyExistsException,
    MissingPatientConsentException,
    MissingRequiredFieldException,
    MissingGuardianConsentException
)

# Configuration du logging
logger = logging.getLogger(__name__)

# Créer un router pour les endpoints des patients
# IMPORTANT: Ne pas inclure /api dans le préfixe, il sera ajouté dans main.py
router = APIRouter(prefix="/patients", tags=["patients"])

def check_role_permission(role: str, allowed_roles: list) -> bool:
    """
    Vérifie si un rôle est autorisé, indépendamment de la casse.
    
    Args:
        role: Le rôle à vérifier
        allowed_roles: Liste des rôles autorisés
        
    Returns:
        bool: True si le rôle est autorisé, False sinon
    """
    if not role:
        return False
    
    # Normaliser le rôle et les rôles autorisés pour la comparaison
    role_lower = role.lower()
    allowed_roles_lower = [r.lower() for r in allowed_roles]
    
    return role_lower in allowed_roles_lower


def get_container():
    """
    Fournit le container d'injection de dépendances.
    """
    return Container()

@router.post("/", response_model=PatientResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreateDTO,
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Crée un nouveau dossier patient.
    
    Args:
        data: Les données pour la création du patient
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        PatientResponseDTO: Le patient créé
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de créer un patient
        user_role = token_payload.get("role", "").lower()  # Conversion en minuscules
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create patient folders"
            )
        
        # Log des données reçues
        logger.info(f"Création d'un nouveau patient avec les données: {data}")
        
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = CreatePatientFolderUseCase(
            patient_repository=container.patient_repository(),
            patient_service=container.patient_service(),
            id_generator=container.id_generator()
        )
        
        # Exécuter le cas d'utilisation
        try:
            result = await use_case.execute(data)
            logger.info(f"Patient créé avec succès: {result.id}")
            return result
        except Exception as e:
            logger.error(f"Erreur pendant l'exécution du cas d'utilisation: {str(e)}")
            raise
    
    except PatientAlreadyExistsException as e:
        logger.error(f"Patient déjà existant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    except MissingRequiredFieldException as e:
        logger.error(f"Champ requis manquant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except MissingGuardianConsentException as e:
        logger.error(f"Consentement du tuteur manquant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except ValueError as e:
        logger.error(f"Erreur de validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la création du patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{patient_id}", response_model=PatientResponseDTO)
async def get_patient(
    patient_id: UUID = Path(..., description="The ID of the patient to get"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère un patient par son ID.
    
    Args:
        patient_id: L'ID du patient à récupérer
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        PatientResponseDTO: Le patient récupéré
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Récupérer l'ID de l'utilisateur à partir du token
        user_id_str = token_payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Token invalide - ID utilisateur manquant")
        try:
            user_id = UUID(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=401, detail="Token invalide - ID utilisateur mal formé")
        
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = GetPatientUseCase(
            patient_repository=container.patient_repository(),
            patient_service=container.patient_service()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(patient_id, user_id)
        
        return result
    
    except PatientNotFoundException as e:
        logger.error(f"Patient non trouvé: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except MissingPatientConsentException as e:
        logger.error(f"Consentement du patient manquant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la récupération du patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.put("/{patient_id}", response_model=PatientResponseDTO)
async def update_patient(
    patient_id: UUID = Path(..., description="The ID of the patient to update"),
    data: PatientUpdateDTO = None,
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Met à jour un patient existant.
    
    Args:
        patient_id: L'ID du patient à mettre à jour
        data: Les données pour la mise à jour du patient
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        PatientResponseDTO: Le patient mis à jour
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de mettre à jour un patient
        user_role = token_payload.get("role", "").lower()
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update patient folders"
            )
        
        # Log des données reçues
        logger.info(f"Mise à jour du patient {patient_id} avec les données: {data}")
        
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = UpdatePatientUseCase(
            patient_repository=container.patient_repository(),
            patient_service=container.patient_service()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(patient_id, data or PatientUpdateDTO())
        
        logger.info(f"Patient {patient_id} mis à jour avec succès")
        return result
    
    except PatientNotFoundException as e:
        logger.error(f"Patient non trouvé: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except MissingRequiredFieldException as e:
        logger.error(f"Champ requis manquant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except ValueError as e:
        logger.error(f"Erreur de validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la mise à jour du patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: UUID = Path(..., description="The ID of the patient to delete"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Supprime un patient.
    
    Args:
        patient_id: L'ID du patient à supprimer
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        None
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de supprimer un patient
        user_role = token_payload.get("role", "").lower()
        
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete patient folders"
            )
        
        logger.info(f"Suppression du patient {patient_id}")
        
        # Exécuter la suppression directement (pas besoin d'un cas d'utilisation dédié)
        patient_repository = container.patient_repository()
        success = await patient_repository.delete(patient_id)
        
        if not success:
            raise PatientNotFoundException(patient_id)
        
        logger.info(f"Patient {patient_id} supprimé avec succès")
        return None
    
    except PatientNotFoundException as e:
        logger.error(f"Patient non trouvé: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la suppression du patient: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/", response_model=PatientListResponseDTO)
async def list_patients(
    skip: int = Query(0, description="Number of patients to skip"),
    limit: int = Query(100, description="Maximum number of patients to return"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """Liste tous les patients avec pagination."""
    try:
        # Vérification des permissions
        user_role = token_payload.get("role", "").lower()  # Get role and convert to lowercase
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        logger.debug(f"User role: {user_role}")  # Add debug logging
        
        if not check_role_permission(user_role, allowed_roles):
            logger.warning(f"Unauthorized access attempt with role: {user_role}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to list patients"
            )
        
        # Récupération des patients
        patient_repository = container.patient_repository()
        try:
            patients = await patient_repository.list_all(skip, limit)
            total = await patient_repository.count()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred"
            )
        
        # Conversion en DTOs
        patient_dtos = [
            PatientResponseDTO(
                id=patient.id,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth,
                gender=patient.gender,
                address=patient.address,
                city=patient.city,
                postal_code=patient.postal_code,
                country=patient.country,
                phone_number=patient.phone_number,
                email=patient.email,
                blood_type=patient.blood_type,
                allergies=patient.allergies,
                chronic_diseases=patient.chronic_diseases,
                current_medications=patient.current_medications,
                has_consent=patient.has_consent,
                gdpr_consent=patient.gdpr_consent,
                consent_date=patient.consent_date,
                insurance_provider=patient.insurance_provider,
                insurance_id=patient.insurance_id,
                notes=patient.notes,
                created_at=patient.created_at,
                updated_at=patient.updated_at,
                is_active=patient.is_active
            )
            for patient in patients
        ]
        
        # Construction de la réponse
        return PatientListResponseDTO(
            patients=patient_dtos,
            total=total,
            skip=skip,
            limit=limit
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la liste des patients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.post("/search", response_model=PatientListResponseDTO)
async def search_patients(
    search_criteria: PatientSearchDTO,
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """Recherche des patients selon différents critères."""
    try:
        # Vérification des permissions
        user_role = token_payload.get("role", "").lower()
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to search patients"
            )
        
        # Recherche des patients
        patient_repository = container.patient_repository()
        patients = await patient_repository.search(
            name=search_criteria.name,
            date_of_birth=search_criteria.date_of_birth,
            email=search_criteria.email,
            phone=search_criteria.phone,
            skip=search_criteria.skip,
            limit=search_criteria.limit
        )
        
        # Compte approximatif pour la pagination
        total = len(patients)
        
        # Conversion en DTOs
        patient_dtos = [
            PatientResponseDTO(
                id=patient.id,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth,
                gender=patient.gender,
                address=patient.address,
                city=patient.city,
                postal_code=patient.postal_code,
                country=patient.country,
                phone_number=patient.phone_number,
                email=patient.email,
                blood_type=patient.blood_type,
                allergies=patient.allergies,
                chronic_diseases=patient.chronic_diseases,
                current_medications=patient.current_medications,
                has_consent=patient.has_consent,
                gdpr_consent=patient.gdpr_consent,
                consent_date=patient.consent_date,
                insurance_provider=patient.insurance_provider,
                insurance_id=patient.insurance_id,
                notes=patient.notes,
                created_at=patient.created_at,
                updated_at=patient.updated_at,
                is_active=patient.is_active
            )
            for patient in patients
        ]
        
        # Construction de la réponse
        return PatientListResponseDTO(
            patients=patient_dtos,
            total=total,
            skip=search_criteria.skip,
            limit=search_criteria.limit
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la recherche de patients: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )