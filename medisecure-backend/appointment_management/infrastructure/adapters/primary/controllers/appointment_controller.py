from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from datetime import date, timedelta, datetime

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
from patient_management.domain.exceptions.patient_exceptions import PatientNotFoundException

# Créer un router pour les endpoints des rendez-vous
router = APIRouter(prefix="/api/appointments", tags=["appointments"])

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
    
    Args:
        data: Les données pour la création du rendez-vous
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentResponseDTO: Le rendez-vous créé
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de créer un rendez-vous
        user_role = token_payload.get("role")
        if user_role not in ["admin", "doctor", "nurse", "receptionist"]:
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
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(data)
        
        return result
    
    except PatientNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{appointment_id}", response_model=AppointmentResponseDTO)
async def get_appointment(
    appointment_id: UUID = Path(..., description="The ID of the appointment to get"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère un rendez-vous par son ID.
    
    Args:
        appointment_id: L'ID du rendez-vous à récupérer
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentResponseDTO: Le rendez-vous récupéré
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Récupérer le rendez-vous
        appointment_repository = container.appointment_repository()
        appointment = await appointment_repository.get_by_id(appointment_id)
        
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )
        
        # Convertir l'entité en DTO de réponse
        return AppointmentResponseDTO(
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
    
    except Exception as e:
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
    
    Args:
        appointment_id: L'ID du rendez-vous à mettre à jour
        data: Les données pour la mise à jour du rendez-vous
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentResponseDTO: Le rendez-vous mis à jour
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de mettre à jour un rendez-vous
        user_role = token_payload.get("role")
        if user_role not in ["admin", "doctor", "nurse", "receptionist"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update appointments"
            )
        
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = UpdateAppointmentUseCase(
            appointment_repository=container.appointment_repository(),
            appointment_service=container.appointment_service()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(appointment_id, data or AppointmentUpdateDTO())
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: UUID = Path(..., description="The ID of the appointment to delete"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Supprime un rendez-vous.
    
    Args:
        appointment_id: L'ID du rendez-vous à supprimer
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        None
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si l'utilisateur a le droit de supprimer un rendez-vous
        user_role = token_payload.get("role")
        if user_role not in ["admin", "doctor"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators and doctors can delete appointments"
            )
        
        # Supprimer le rendez-vous
        appointment_repository = container.appointment_repository()
        success = await appointment_repository.delete(appointment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with ID {appointment_id} not found"
            )
        
        return None
    
    except Exception as e:
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
    
    Args:
        patient_id: L'ID du patient
        skip: Le nombre de rendez-vous à sauter
        limit: Le nombre maximum de rendez-vous à retourner
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentListResponseDTO: La liste des rendez-vous du patient
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Créer le cas d'utilisation avec les dépendances nécessaires
        use_case = GetPatientAppointmentsUseCase(
            appointment_repository=container.appointment_repository(),
            patient_repository=container.patient_repository()
        )
        
        # Exécuter le cas d'utilisation
        result = await use_case.execute(patient_id, skip, limit)
        
        return result
    
    except PatientNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/doctor/{doctor_id}", response_model=AppointmentListResponseDTO)
async def get_doctor_appointments(
    doctor_id: UUID = Path(..., description="The ID of the doctor"),
    skip: int = Query(0, description="Number of appointments to skip"),
    limit: int = Query(100, description="Maximum number of appointments to return"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère les rendez-vous d'un médecin.
    
    Args:
        doctor_id: L'ID du médecin
        skip: Le nombre de rendez-vous à sauter
        limit: Le nombre maximum de rendez-vous à retourner
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentListResponseDTO: La liste des rendez-vous du médecin
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Récupérer les rendez-vous du médecin
        appointment_repository = container.appointment_repository()
        appointments = await appointment_repository.get_by_doctor(doctor_id, skip, limit)
        
        # Compter le nombre total de rendez-vous (approximatif sans pagination)
        total = len(appointments)
        
        # Convertir les entités en DTOs de réponse
        appointment_dtos = []
        for appointment in appointments:
            appointment_dtos.append(
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
            )
        
        # Construire la réponse
        response = AppointmentListResponseDTO(
            appointments=appointment_dtos,
            total=total,
            skip=skip,
            limit=limit
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/calendar", response_model=AppointmentListResponseDTO)
async def get_calendar_appointments(
    year: int = Query(..., description="Year of the calendar"),
    month: int = Query(..., description="Month of the calendar (1-12)"),
    token_payload: Dict[str, Any] = Depends(extract_token_payload),
    container: Container = Depends(get_container)
):
    """
    Récupère les rendez-vous pour un mois spécifique.
    
    Args:
        year: L'année du calendrier
        month: Le mois du calendrier (1-12)
        token_payload: Les informations du token JWT
        container: Le container d'injection de dépendances
        
    Returns:
        AppointmentListResponseDTO: La liste des rendez-vous pour le mois spécifié
        
    Raises:
        HTTPException: En cas d'erreur
    """
    try:
        # Vérifier si le mois est valide
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Month must be between 1 and 12"
            )
        
        # Calculer la plage de dates pour le mois
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Récupérer les rendez-vous pour cette plage de dates
        appointment_repository = container.appointment_repository()
        appointments = await appointment_repository.get_by_date_range(start_date, end_date)
        
        # Compter le nombre total de rendez-vous
        total = len(appointments)
        
        # Convertir les entités en DTOs de réponse
        appointment_dtos = []
        for appointment in appointments:
            appointment_dtos.append(
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
            )
        
        # Construire la réponse
        response = AppointmentListResponseDTO(
            appointments=appointment_dtos,
            total=total,
            skip=0,
            limit=total
        )
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )