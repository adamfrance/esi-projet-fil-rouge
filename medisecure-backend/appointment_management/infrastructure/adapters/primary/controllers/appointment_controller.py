# medisecure-backend/appointment_management/infrastructure/adapters/primary/controllers/appointment_controller.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from datetime import date, timedelta, datetime
import logging

from shared.services.authenticator.extract_token import extract_token_payload
from shared.container.container import Container
from appointment_management.application.dtos.appointment_dtos import (
    AppointmentCreateDTO,
    AppointmentUpdateDTO,
    AppointmentResponseDTO,
    AppointmentListResponseDTO
)
from appointment_management.application.usecases.schedule_appointment_usecase import ScheduleAppointmentUseCase
from appointment_management.application.usecases.update_appointment_usecase import UpdateAppointmentUseCase
from appointment_management.application.usecases.get_patient_appointments_usecase import GetPatientAppointmentsUseCase
from appointment_management.domain.entities.appointment import AppointmentStatus
from patient_management.domain.exceptions.patient_exceptions import PatientNotFoundException

# Configuration du logging
logger = logging.getLogger(__name__)

# Créer un router pour les endpoints des rendez-vous
router = APIRouter(prefix="/appointments", tags=["appointments"])

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

@router.post("/", response_model=AppointmentResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    data: AppointmentCreateDTO,
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Crée un nouveau rendez-vous.
    """
    try:
        # Journaliser les données reçues
        logger.info(f"Données reçues pour la création d'un rendez-vous: {data}")
        
        # Vérifier si l'utilisateur a le droit de créer un rendez-vous
        user_role = token_payload.get("role", "")
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create appointments"
            )
        
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = ScheduleAppointmentUseCase(
            appointment_repository=container.appointment_repository(),
            patient_repository=container.patient_repository(),
            appointment_service=container.appointment_service(),
            id_generator=container.id_generator()
        )
        
        # Valider les dates avant de les envoyer au cas d'utilisation
        try:
            # Vérifier et formater les dates si nécessaire
            if isinstance(data.start_time, str):
                data.start_time = datetime.fromisoformat(data.start_time.replace('Z', '+00:00'))
            if isinstance(data.end_time, str):
                data.end_time = datetime.fromisoformat(data.end_time.replace('Z', '+00:00'))
                
            logger.info(f"Dates après conversion: start_time={data.start_time}, end_time={data.end_time}")
        except ValueError as e:
            logger.error(f"Erreur lors de la conversion des dates: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}"
            )
        
        # Exécuter le cas d'utilisation
        try:
            logger.info("Tentative d'exécution du cas d'utilisation ScheduleAppointmentUseCase")
            result = await use_case.execute(data)
            logger.info(f"Rendez-vous créé avec succès: {result.id}")
            return result
        except Exception as e:
            logger.exception(f"Erreur pendant l'exécution du cas d'utilisation: {str(e)}")
            raise
    
    except PatientNotFoundException as e:
        logger.error(f"Patient non trouvé: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except ValueError as e:
        logger.error(f"Erreur de validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la création du rendez-vous: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

# Ajout des autres routes nécessaires
@router.get("/{appointment_id}", response_model=AppointmentResponseDTO)
async def get_appointment(
    appointment_id: UUID = Path(..., description="The ID of the appointment to get"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère un rendez-vous par son ID.
    """
    try:
        # Obtenir le repository
        appointment_repository = container.appointment_repository()
        
        # Récupérer le rendez-vous
        appointment = await appointment_repository.get_by_id(appointment_id)
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )
        
        # Convertir en DTO de réponse
        response = AppointmentResponseDTO(
            id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            start_time=appointment.start_time,
            end_time=appointment.end_time,
            status=appointment.status.value,
            reason=appointment.reason,
            notes=appointment.notes,
            created_at=appointment.created_at,
            updated_at=appointment.updated_at,
            is_active=appointment.is_active
        )
        
        return response
    
    except Exception as e:
        logger.exception(f"Erreur lors de la récupération du rendez-vous {appointment_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.put("/{appointment_id}", response_model=AppointmentResponseDTO)
async def update_appointment(
    appointment_id: UUID = Path(..., description="The ID of the appointment to update"),
    data: AppointmentUpdateDTO = None,
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Met à jour un rendez-vous existant.
    """
    try:
        # Vérifier les permissions
        user_role = token_payload.get("role", "")
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update appointments"
            )
        
        # Créer le cas d'utilisation
        use_case = UpdateAppointmentUseCase(
            appointment_repository=container.appointment_repository(),
            appointment_service=container.appointment_service()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(appointment_id, data or AppointmentUpdateDTO())
        
        return result
        
    except ValueError as e:
        logger.error(f"Erreur de validation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la mise à jour du rendez-vous: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/patient/{patient_id}", response_model=AppointmentListResponseDTO)
async def get_patient_appointments(
    patient_id: UUID = Path(..., description="The ID of the patient"),
    skip: int = Query(0, description="Number of appointments to skip"),
    limit: int = Query(100, description="Maximum number of appointments to return"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère les rendez-vous d'un patient.
    """
    try:
        # Créer le cas d'utilisation
        use_case = GetPatientAppointmentsUseCase(
            appointment_repository=container.appointment_repository(),
            patient_repository=container.patient_repository()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(patient_id, skip, limit)
        
        return result
        
    except PatientNotFoundException as e:
        logger.error(f"Patient non trouvé: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la récupération des rendez-vous: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/", response_model=AppointmentListResponseDTO)
async def list_appointments(
    skip: int = Query(0, description="Number of appointments to skip"),
    limit: int = Query(100, description="Maximum number of appointments to return"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Liste tous les rendez-vous avec pagination.
    """
    try:
        # Vérifier les permissions
        user_role = token_payload.get("role", "")
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to list appointments"
            )
        
        # Récupérer le repository
        appointment_repository = container.appointment_repository()
        
        # Récupérer les rendez-vous
        appointments = await appointment_repository.list_all(skip, limit)
        total = await appointment_repository.count()
        
        # Convertir en DTOs
        appointment_dtos = [
            AppointmentResponseDTO(
                id=appointment.id,
                patient_id=appointment.patient_id,
                doctor_id=appointment.doctor_id,
                start_time=appointment.start_time,
                end_time=appointment.end_time,
                status=appointment.status.value,
                reason=appointment.reason,
                notes=appointment.notes,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at,
                is_active=appointment.is_active
            )
            for appointment in appointments
        ]
        
        # Construire la réponse
        return AppointmentListResponseDTO(
            appointments=appointment_dtos,
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la récupération des rendez-vous: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/calendar/", response_model=AppointmentListResponseDTO)
async def get_calendar(
    year: int = Query(..., description="Year to fetch the calendar for"),
    month: int = Query(..., description="Month to fetch the calendar for"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère les rendez-vous pour un mois spécifique (pour l'affichage calendrier).
    """
    try:
        # Vérifier les permissions
        user_role = token_payload.get("role", "")
        allowed_roles = ["admin", "doctor", "nurse", "receptionist"]
        
        if not check_role_permission(user_role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view the calendar"
            )
        
        # Déterminer les dates de début et de fin du mois
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Récupérer le repository
        appointment_repository = container.appointment_repository()
        
        # Récupérer les rendez-vous dans cette plage de dates
        appointments = await appointment_repository.get_by_date_range(start_date, end_date)
        
        # Convertir en DTOs
        appointment_dtos = [
            AppointmentResponseDTO(
                id=appointment.id,
                patient_id=appointment.patient_id,
                doctor_id=appointment.doctor_id,
                start_time=appointment.start_time,
                end_time=appointment.end_time,
                status=appointment.status.value,
                reason=appointment.reason,
                notes=appointment.notes,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at,
                is_active=appointment.is_active
            )
            for appointment in appointments
        ]
        
        # Construire la réponse
        return AppointmentListResponseDTO(
            appointments=appointment_dtos,
            total=len(appointments),
            skip=0,
            limit=len(appointments)
        )
        
    except Exception as e:
        logger.exception(f"Erreur inattendue lors de la récupération du calendrier: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.get("/test")
async def test_endpoint():
    """Test endpoint sans authentification"""
    return {"message": "Test réussi", "timestamp": datetime.now().isoformat()}