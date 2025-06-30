# medisecure-backend/appointment_management/infrastructure/adapters/secondary/postgres_appointment_repository.py
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, and_, or_, func, text
import logging

from appointment_management.domain.entities.appointment import Appointment, AppointmentStatus
from appointment_management.domain.ports.secondary.appointment_repository_protocol import AppointmentRepositoryProtocol
from shared.infrastructure.database.models.appointment_model import AppointmentModel, AppointmentStatus as AppointmentStatusModel

# Configuration du logging
logger = logging.getLogger(__name__)

class PostgresAppointmentRepository(AppointmentRepositoryProtocol):
    """
    Adaptateur secondaire pour le repository des rendez-vous avec PostgreSQL.
    Implémente le port AppointmentRepositoryProtocol.
    """
    
    def __init__(self, session_factory):
        """
        Initialise le repository avec une factory de session SQLAlchemy.
        
        Args:
            session_factory: La factory de session SQLAlchemy à utiliser
        """
        self.session_factory = session_factory
    
    async def get_by_id(self, appointment_id: UUID) -> Optional[Appointment]:
        """
        Récupère un rendez-vous par son ID.
        
        Args:
            appointment_id: L'ID du rendez-vous à récupérer
            
        Returns:
            Optional[Appointment]: Le rendez-vous trouvé ou None si non trouvé
        """
        try:
            logger.debug(f"Récupération du rendez-vous avec ID: {appointment_id}")
            query = select(AppointmentModel).where(AppointmentModel.id == appointment_id)
            result = await self.session.execute(query)
            appointment_model = result.scalar_one_or_none()
            
            if not appointment_model:
                logger.debug(f"Rendez-vous avec ID {appointment_id} non trouvé")
                return None
            
            logger.debug(f"Rendez-vous trouvé: {appointment_model.id}")
            return self._map_to_entity(appointment_model)
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du rendez-vous {appointment_id}: {str(e)}")
            raise
    
    async def create(self, appointment: Appointment) -> Appointment:
        """
        Crée un nouveau rendez-vous.
        
        Args:
            appointment: Le rendez-vous à créer
            
        Returns:
            Appointment: Le rendez-vous créé avec son ID généré
        """
        try:
            logger.info(f"Création d'un nouveau rendez-vous: {appointment.id}")
            logger.debug(f"Données du rendez-vous: patient_id={appointment.patient_id}, doctor_id={appointment.doctor_id}")
            logger.debug(f"Dates: start_time={appointment.start_time}, end_time={appointment.end_time}")
            
            # S'assurer que les ID sont de type UUID
            patient_id = appointment.patient_id if isinstance(appointment.patient_id, UUID) else UUID(str(appointment.patient_id))
            doctor_id = appointment.doctor_id if isinstance(appointment.doctor_id, UUID) else UUID(str(appointment.doctor_id))
            
            # Créer le modèle avec les bonnes conversions de types
            appointment_model = AppointmentModel(
                id=appointment.id,
                patient_id=patient_id,
                doctor_id=doctor_id,
                start_time=appointment.start_time,
                end_time=appointment.end_time,
                status=AppointmentStatusModel(appointment.status.value),
                reason=appointment.reason,
                notes=appointment.notes,
                created_at=appointment.created_at,
                updated_at=appointment.updated_at,
                is_active=appointment.is_active
            )
            
            # Utiliser un bloc try spécifique pour l'ajout à la session et le commit
            try:
                self.session.add(appointment_model)
                await self.session.flush()  # Flush pour détecter les erreurs avant le commit
                await self.session.commit()
                await self.session.refresh(appointment_model)
                
                logger.info(f"Rendez-vous créé avec succès: {appointment_model.id}")
                return self._map_to_entity(appointment_model)
            except Exception as e:
                await self.session.rollback()
                logger.error(f"Erreur lors de la persistance du rendez-vous: {str(e)}")
                # Essayons d'identifier plus précisément l'erreur
                if "violates foreign key constraint" in str(e):
                    logger.error("Violation de clé étrangère détectée")
                    raise ValueError(f"Une référence à une entité inexistante a été trouvée: {str(e)}")
                elif "unique constraint" in str(e):
                    logger.error("Violation de contrainte d'unicité détectée")
                    raise ValueError(f"Un rendez-vous similaire existe déjà: {str(e)}")
                raise
                
        except Exception as e:
            logger.exception(f"Erreur lors de la création du rendez-vous: {str(e)}")
            raise
    
    async def update(self, appointment: Appointment) -> Appointment:
        """
        Met à jour un rendez-vous existant.
        
        Args:
            appointment: Le rendez-vous à mettre à jour
            
        Returns:
            Appointment: Le rendez-vous mis à jour
        """
        try:
            logger.info(f"Mise à jour du rendez-vous: {appointment.id}")
            
            # S'assurer que les ID sont de type UUID
            patient_id = appointment.patient_id if isinstance(appointment.patient_id, UUID) else UUID(str(appointment.patient_id))
            doctor_id = appointment.doctor_id if isinstance(appointment.doctor_id, UUID) else UUID(str(appointment.doctor_id))
            
            # Vérifier d'abord si le rendez-vous existe
            existing_appointment = await self.get_by_id(appointment.id)
            if not existing_appointment:
                logger.error(f"Tentative de mise à jour d'un rendez-vous inexistant: {appointment.id}")
                raise ValueError(f"Le rendez-vous avec l'ID {appointment.id} n'existe pas")
            
            # Préparer la requête de mise à jour
            query = (
                update(AppointmentModel)
                .where(AppointmentModel.id == appointment.id)
                .values(
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time,
                    status=AppointmentStatusModel(appointment.status.value),
                    reason=appointment.reason,
                    notes=appointment.notes,
                    updated_at=datetime.utcnow(),
                    is_active=appointment.is_active
                )
            )
            
            # Exécuter la mise à jour
            try:
                await self.session.execute(query)
                await self.session.commit()
                
                # Récupérer le rendez-vous mis à jour
                updated_appointment = await self.get_by_id(appointment.id)
                logger.info(f"Rendez-vous {appointment.id} mis à jour avec succès")
                return updated_appointment
            except Exception as e:
                await self.session.rollback()
                logger.error(f"Erreur lors de la mise à jour en base de données: {str(e)}")
                raise
                
        except Exception as e:
            logger.exception(f"Erreur lors de la mise à jour du rendez-vous {appointment.id}: {str(e)}")
            raise
    
    async def delete(self, appointment_id: UUID) -> bool:
        """
        Supprime un rendez-vous.
        
        Args:
            appointment_id: L'ID du rendez-vous à supprimer
            
        Returns:
            bool: True si le rendez-vous a été supprimé, False sinon
        """
        try:
            logger.info(f"Suppression du rendez-vous: {appointment_id}")
            
            # Vérifier d'abord si le rendez-vous existe
            existing_appointment = await self.get_by_id(appointment_id)
            if not existing_appointment:
                logger.warning(f"Tentative de suppression d'un rendez-vous inexistant: {appointment_id}")
                return False
            
            # Préparer la requête de suppression
            query = delete(AppointmentModel).where(AppointmentModel.id == appointment_id)
            
            # Exécuter la suppression
            try:
                result = await self.session.execute(query)
                await self.session.commit()
                
                if result.rowcount == 0:
                    logger.warning(f"Aucune ligne affectée lors de la suppression du rendez-vous {appointment_id}")
                    return False
                
                logger.info(f"Rendez-vous {appointment_id} supprimé avec succès")
                return True
            except Exception as e:
                await self.session.rollback()
                logger.error(f"Erreur lors de la suppression en base de données: {str(e)}")
                raise
                
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du rendez-vous {appointment_id}: {str(e)}")
            raise
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """
        Liste tous les rendez-vous avec pagination.
        
        Args:
            skip: Le nombre de rendez-vous à sauter
            limit: Le nombre maximum de rendez-vous à retourner
            
        Returns:
            List[Appointment]: La liste des rendez-vous
        """
        try:
            logger.debug(f"Liste de tous les rendez-vous (skip={skip}, limit={limit})")
            
            # Construire la requête avec pagination
            query = select(AppointmentModel).order_by(AppointmentModel.start_time.desc()).offset(skip).limit(limit)
            
            # Exécuter la requête
            result = await self.session.execute(query)
            appointment_models = result.scalars().all()
            
            logger.debug(f"Nombre de rendez-vous récupérés: {len(appointment_models)}")
            return [self._map_to_entity(appointment_model) for appointment_model in appointment_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de la liste des rendez-vous: {str(e)}")
            raise
    
    async def get_by_patient(self, patient_id: UUID, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """
        Récupère les rendez-vous d'un patient.
        
        Args:
            patient_id: L'ID du patient
            skip: Le nombre de rendez-vous à sauter
            limit: Le nombre maximum de rendez-vous à retourner
            
        Returns:
            List[Appointment]: La liste des rendez-vous du patient
        """
        try:
            logger.debug(f"Récupération des rendez-vous du patient {patient_id}")
            
            # S'assurer que l'ID est de type UUID
            patient_id = patient_id if isinstance(patient_id, UUID) else UUID(str(patient_id))
            
            # Construire la requête
            query = (
                select(AppointmentModel)
                .where(AppointmentModel.patient_id == patient_id)
                .order_by(AppointmentModel.start_time.desc())
                .offset(skip)
                .limit(limit)
            )
            
            # Exécuter la requête
            result = await self.session.execute(query)
            appointment_models = result.scalars().all()
            
            logger.debug(f"Nombre de rendez-vous récupérés pour le patient {patient_id}: {len(appointment_models)}")
            return [self._map_to_entity(appointment_model) for appointment_model in appointment_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération des rendez-vous du patient {patient_id}: {str(e)}")
            raise
    
    async def get_by_doctor(self, doctor_id: UUID, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """
        Récupère les rendez-vous d'un médecin.
        
        Args:
            doctor_id: L'ID du médecin
            skip: Le nombre de rendez-vous à sauter
            limit: Le nombre maximum de rendez-vous à retourner
            
        Returns:
            List[Appointment]: La liste des rendez-vous du médecin
        """
        try:
            logger.debug(f"Récupération des rendez-vous du médecin {doctor_id}")
            
            # S'assurer que l'ID est de type UUID
            doctor_id = doctor_id if isinstance(doctor_id, UUID) else UUID(str(doctor_id))
            
            # Construire la requête
            query = (
                select(AppointmentModel)
                .where(AppointmentModel.doctor_id == doctor_id)
                .order_by(AppointmentModel.start_time.desc())
                .offset(skip)
                .limit(limit)
            )
            
            # Exécuter la requête
            result = await self.session.execute(query)
            appointment_models = result.scalars().all()
            
            logger.debug(f"Nombre de rendez-vous récupérés pour le médecin {doctor_id}: {len(appointment_models)}")
            return [self._map_to_entity(appointment_model) for appointment_model in appointment_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération des rendez-vous du médecin {doctor_id}: {str(e)}")
            raise
    
    async def get_by_date_range(self, start_date: date, end_date: date, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """
        Récupère les rendez-vous dans une plage de dates.
        
        Args:
            start_date: La date de début
            end_date: La date de fin
            skip: Le nombre de rendez-vous à sauter
            limit: Le nombre maximum de rendez-vous à retourner
            
        Returns:
            List[Appointment]: La liste des rendez-vous dans la plage de dates
        """
        try:
            logger.debug(f"Récupération des rendez-vous entre {start_date} et {end_date}")
            
            # Convertir les dates en datetime pour la requête
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            # Construire la requête
            query = (
                select(AppointmentModel)
                .where(
                    or_(
                        and_(
                            AppointmentModel.start_time >= start_datetime,
                            AppointmentModel.start_time <= end_datetime
                        ),
                        and_(
                            AppointmentModel.end_time >= start_datetime,
                            AppointmentModel.end_time <= end_datetime
                        ),
                        and_(
                            AppointmentModel.start_time <= start_datetime,
                            AppointmentModel.end_time >= end_datetime
                        )
                    )
                )
                .order_by(AppointmentModel.start_time)
                .offset(skip)
                .limit(limit)
            )
            
            # Exécuter la requête
            result = await self.session.execute(query)
            appointment_models = result.scalars().all()
            
            logger.debug(f"Nombre de rendez-vous récupérés entre {start_date} et {end_date}: {len(appointment_models)}")
            return [self._map_to_entity(appointment_model) for appointment_model in appointment_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération des rendez-vous par plage de dates: {str(e)}")
            raise
    
    async def count(self) -> int:
        """
        Compte le nombre total de rendez-vous.
        
        Returns:
            int: Le nombre total de rendez-vous
        """
        try:
            logger.debug("Comptage du nombre total de rendez-vous")
            
            # Optimisation avec COUNT(*)
            query = select(func.count()).select_from(AppointmentModel)
            
            # Exécuter la requête
            result = await self.session.execute(query)
            count = result.scalar_one_or_none() or 0
            
            logger.debug(f"Nombre total de rendez-vous: {count}")
            return count
        except Exception as e:
            logger.exception(f"Erreur lors du comptage des rendez-vous: {str(e)}")
            raise
    
    def _map_to_entity(self, appointment_model: AppointmentModel) -> Appointment:
        """
        Convertit un modèle SQLAlchemy en entité du domaine.
        
        Args:
            appointment_model: Le modèle SQLAlchemy à convertir
            
        Returns:
            Appointment: L'entité du domaine correspondante
        """
        try:
            # S'assurer que le statut est valide
            status_value = appointment_model.status.value if hasattr(appointment_model.status, 'value') else str(appointment_model.status)
            
            # Créer l'entité
            return Appointment(
                id=appointment_model.id,
                patient_id=appointment_model.patient_id,
                doctor_id=appointment_model.doctor_id,
                start_time=appointment_model.start_time,
                end_time=appointment_model.end_time,
                status=AppointmentStatus(status_value),
                reason=appointment_model.reason,
                notes=appointment_model.notes,
                created_at=appointment_model.created_at,
                updated_at=appointment_model.updated_at,
                is_active=appointment_model.is_active
            )
        except Exception as e:
            logger.exception(f"Erreur lors de la conversion du modèle en entité: {str(e)}")
            # Journaliser plus de détails sur le modèle
            logger.error(f"Détails du modèle: id={appointment_model.id}, status={getattr(appointment_model, 'status', 'N/A')}")
            raise ValueError(f"Erreur lors de la conversion du modèle de rendez-vous en entité: {str(e)}")