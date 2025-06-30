# medisecure-backend/patient_management/infrastructure/adapters/secondary/postgres_patient_repository.py
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, or_, and_, func
import logging

from patient_management.domain.entities.patient import Patient
from patient_management.domain.ports.secondary.patient_repository_protocol import PatientRepositoryProtocol
from shared.infrastructure.database.models.patient_model import PatientModel

# Configuration du logging
logger = logging.getLogger(__name__)

class PostgresPatientRepository(PatientRepositoryProtocol):
    """
    Adaptateur secondaire pour le repository des patients avec PostgreSQL.
    Implémente le port PatientRepositoryProtocol.
    """
    
    def __init__(self, session_factory):
        """
        Initialise le repository avec une factory de session SQLAlchemy.
        
        Args:
            session_factory: La factory de session SQLAlchemy à utiliser
        """
        self.session_factory = session_factory
    
    async def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """..."""
        try:
            logger.debug(f"Récupération du patient avec ID: {patient_id}")
            async with self.session_factory() as session:
                query = select(PatientModel).where(PatientModel.id == patient_id)
                result = await session.execute(query)
                patient_model = result.scalar_one_or_none()
                
                if not patient_model:
                    logger.debug(f"Patient avec ID {patient_id} non trouvé")
                    return None
                
                logger.debug(f"Patient trouvé: {patient_model.id}")
                return self._map_to_entity(patient_model)
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du patient {patient_id}: {str(e)}")
            raise
    
    async def get_by_email(self, email: str) -> Optional[Patient]:
        try:
            logger.debug(f"Récupération du patient avec email: {email}")
            async with self.session_factory() as session:
                query = select(PatientModel).where(PatientModel.email == email)
                result = await session.execute(query)
                patient_model = result.scalar_one_or_none()
                
                if not patient_model:
                    logger.debug(f"Patient avec email {email} non trouvé")
                    return None
                
                logger.debug(f"Patient trouvé: {patient_model.id}")
                return self._map_to_entity(patient_model)
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du patient par email {email}: {str(e)}")
            raise
    
    async def create(self, patient: Patient) -> Patient:
        """..."""
        try:
            logger.info(f"Création d'un nouveau patient: {patient.first_name} {patient.last_name}")
            
            async with self.session_factory() as session:
                patient_model = PatientModel(
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
                    consent_date=patient.consent_date,
                    gdpr_consent=patient.gdpr_consent,
                    insurance_provider=patient.insurance_provider,
                    insurance_id=patient.insurance_id,
                    notes=patient.notes,
                    created_at=patient.created_at,
                    updated_at=patient.updated_at,
                    is_active=patient.is_active
                )
                
                session.add(patient_model)
                await session.commit()
                await session.refresh(patient_model)
                
                logger.info(f"Patient créé avec succès: {patient_model.id}")
                return self._map_to_entity(patient_model)
        except Exception as e:
            logger.exception(f"Erreur lors de la création du patient: {str(e)}")
            raise
    
    async def update(self, patient: Patient) -> Patient:
        """
        Met à jour un patient existant.
        
        Args:
            patient: Le patient à mettre à jour
            
        Returns:
            Patient: Le patient mis à jour
        """
        try:
            logger.info(f"Mise à jour du patient: {patient.id}")
            
            query = (
                update(PatientModel)
                .where(PatientModel.id == patient.id)
                .values(
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
                    consent_date=patient.consent_date,
                    gdpr_consent=patient.gdpr_consent,
                    insurance_provider=patient.insurance_provider,
                    insurance_id=patient.insurance_id,
                    notes=patient.notes,
                    updated_at=datetime.utcnow(),
                    is_active=patient.is_active
                )
            )
            
            await self.session.execute(query)
            await self.session.commit()
            
            # Récupérer le patient mis à jour pour le retourner
            updated_patient = await self.get_by_id(patient.id)
            logger.info(f"Patient {patient.id} mis à jour avec succès")
            return updated_patient
        except Exception as e:
            logger.exception(f"Erreur lors de la mise à jour du patient {patient.id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def delete(self, patient_id: UUID) -> bool:
        """
        Supprime un patient.
        
        Args:
            patient_id: L'ID du patient à supprimer
            
        Returns:
            bool: True si le patient a été supprimé, False sinon
        """
        try:
            logger.info(f"Suppression du patient {patient_id}")
            
            # Vérifier si le patient existe
            patient = await self.get_by_id(patient_id)
            if not patient:
                logger.warning(f"Tentative de suppression d'un patient inexistant: {patient_id}")
                return False
            
            # Supprimer le patient
            query = delete(PatientModel).where(PatientModel.id == patient_id)
            result = await self.session.execute(query)
            
            if result.rowcount == 0:
                logger.warning(f"Aucune ligne affectée lors de la suppression du patient {patient_id}")
                return False
            
            await self.session.commit()
            logger.info(f"Patient {patient_id} supprimé avec succès")
            return True
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du patient {patient_id}: {str(e)}")
            await self.session.rollback()
            raise
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Patient]:
        """..."""
        try:
            logger.debug(f"Récupération de la liste des patients (skip={skip}, limit={limit})")
            async with self.session_factory() as session:
                query = select(PatientModel).offset(skip).limit(limit)
                result = await session.execute(query)
                patient_models = result.scalars().all()
                
                logger.debug(f"Nombre de patients récupérés: {len(patient_models)}")
                return [self._map_to_entity(patient_model) for patient_model in patient_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de la liste des patients: {str(e)}")
            raise
    
    async def search(
        self,
        name: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Patient]:
        try:
            logger.debug(f"Recherche de patients avec critères: name={name}, date_of_birth={date_of_birth}, email={email}, phone={phone}")
            
            # Construire la requête de base
            query = select(PatientModel)
            
            # Ajouter les filtres si fournis
            filters = []
            
            if name:
                filters.append(
                    or_(
                        PatientModel.first_name.ilike(f"%{name}%"),
                        PatientModel.last_name.ilike(f"%{name}%")
                    )
                )
            
            if date_of_birth:
                filters.append(PatientModel.date_of_birth == date_of_birth)
            
            if email:
                filters.append(PatientModel.email == email)
            
            if phone:
                filters.append(PatientModel.phone_number.ilike(f"%{phone}%"))
            
            # Ajouter tous les filtres à la requête
            if filters:
                query = query.where(and_(*filters))
            
            # Ajouter la pagination
            query = query.offset(skip).limit(limit)
            
            # Exécuter la requête
            async with self.session_factory() as session:
                result = await session.execute(query)
                patient_models = result.scalars().all()
            
            logger.debug(f"Nombre de patients trouvés: {len(patient_models)}")
            return [self._map_to_entity(patient_model) for patient_model in patient_models]
        except Exception as e:
            logger.exception(f"Erreur lors de la recherche de patients: {str(e)}")
            raise
        
    async def count(self) -> int:
        try:
            logger.debug("Comptage du nombre total de patients")
            async with self.session_factory() as session:
                query = select(func.count()).select_from(PatientModel)
                result = await session.execute(query)
                count = result.scalar_one()
                logger.debug(f"Nombre total de patients: {count}")
                return count
        except Exception as e:
            logger.exception(f"Erreur lors du comptage des patients: {str(e)}")
            raise
    
    def _map_to_entity(self, patient_model: PatientModel) -> Patient:
        """
        Convertit un modèle SQLAlchemy en entité du domaine.
        
        Args:
            patient_model: Le modèle SQLAlchemy à convertir
            
        Returns:
            Patient: L'entité du domaine correspondante
        """
        return Patient(
            id=patient_model.id,
            first_name=patient_model.first_name,
            last_name=patient_model.last_name,
            date_of_birth=patient_model.date_of_birth,
            gender=patient_model.gender,
            address=patient_model.address,
            city=patient_model.city,
            postal_code=patient_model.postal_code,
            country=patient_model.country,
            phone_number=patient_model.phone_number,
            email=patient_model.email,
            blood_type=patient_model.blood_type,
            allergies=patient_model.allergies or {},
            chronic_diseases=patient_model.chronic_diseases or {},
            current_medications=patient_model.current_medications or {},
            has_consent=patient_model.has_consent,
            consent_date=patient_model.consent_date,
            gdpr_consent=patient_model.gdpr_consent,
            insurance_provider=patient_model.insurance_provider,  # Correction ici
            insurance_id=patient_model.insurance_id,
            notes=patient_model.notes,
            created_at=patient_model.created_at,
            updated_at=patient_model.updated_at,
            is_active=patient_model.is_active
        )