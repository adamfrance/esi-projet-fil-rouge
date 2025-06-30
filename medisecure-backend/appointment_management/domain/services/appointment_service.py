# medisecure-backend/appointment_management/domain/services/appointment_service.py
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
from uuid import UUID
import logging

from appointment_management.domain.entities.appointment import Appointment, AppointmentStatus

# Configuration du logging
logger = logging.getLogger(__name__)

class AppointmentService:
    """
    Service du domaine pour les opérations liées aux rendez-vous.
    Contient la logique métier pour la gestion des rendez-vous.
    """
    
    def validate_appointment_times(self, start_time: datetime, end_time: datetime) -> None:
        """
        Valide les heures de début et de fin d'un rendez-vous.
        
        Args:
            start_time: L'heure de début du rendez-vous
            end_time: L'heure de fin du rendez-vous
            
        Raises:
            ValueError: Si l'heure de fin est avant ou égale à l'heure de début
                       ou si les heures ne sont pas valides
        """
        # Vérifier que les dates sont bien des objets datetime
        if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
            logger.error(f"Types de dates invalides: start_time={type(start_time)}, end_time={type(end_time)}")
            raise ValueError("Les heures de début et de fin doivent être des objets datetime")
        
        # Vérifier que l'heure de début est avant l'heure de fin
        if end_time <= start_time:
            logger.error(f"Heure de fin ({end_time}) avant ou égale à l'heure de début ({start_time})")
            raise ValueError("L'heure de fin doit être après l'heure de début")
        
        # Vérifier que la durée du rendez-vous est raisonnable (par exemple, pas plus de 24h)
        duration = end_time - start_time
        if duration > timedelta(hours=24):
            logger.warning(f"Durée de rendez-vous très longue détectée: {duration}")
            # Ce n'est qu'un avertissement, pas une erreur
    
    def check_appointment_overlap(
        self, 
        existing_appointments: List[Appointment], 
        start_time: datetime, 
        end_time: datetime,
        appointment_id: Optional[UUID] = None
    ) -> bool:
        """
        Vérifie si un rendez-vous chevauche des rendez-vous existants.
        
        Args:
            existing_appointments: Liste des rendez-vous existants à vérifier
            start_time: L'heure de début du nouveau rendez-vous
            end_time: L'heure de fin du nouveau rendez-vous
            appointment_id: L'ID du rendez-vous à exclure de la vérification (pour les mises à jour)
            
        Returns:
            bool: True si le rendez-vous chevauche un autre, False sinon
        """
        # Journaliser le nombre de rendez-vous à vérifier
        logger.debug(f"Vérification de chevauchement parmi {len(existing_appointments)} rendez-vous existants")
        
        for appointment in existing_appointments:
            # Ignorer le rendez-vous lui-même pour les mises à jour
            if appointment_id and appointment.id == appointment_id:
                continue
                
            # Ignorer les rendez-vous annulés
            if appointment.status == AppointmentStatus.CANCELLED:
                continue
            
            # Ignorer les rendez-vous terminés
            if appointment.status == AppointmentStatus.COMPLETED:
                continue
                
            # Vérifier si les plages horaires se chevauchent
            # Un chevauchement existe si l'une des plages commence avant que l'autre ne se termine
            # et se termine après que l'autre n'ait commencé
            if (start_time < appointment.end_time and end_time > appointment.start_time):
                logger.info(f"Chevauchement détecté avec le rendez-vous {appointment.id}")
                logger.debug(f"Nouveau: {start_time} - {end_time}, Existant: {appointment.start_time} - {appointment.end_time}")
                return True
                
        # Aucun chevauchement trouvé
        logger.debug("Aucun chevauchement de rendez-vous détecté")
        return False
    
    def get_available_slots(
        self, 
        existing_appointments: List[Appointment], 
        date_to_check: date,
        slot_duration_minutes: int = 30,
        start_hour: int = 8,
        end_hour: int = 18
    ) -> List[Dict]:
        """
        Trouve les créneaux disponibles pour une date donnée.
        
        Args:
            existing_appointments: Liste des rendez-vous existants pour cette date
            date_to_check: La date pour laquelle chercher des créneaux
            slot_duration_minutes: La durée d'un créneau en minutes
            start_hour: L'heure de début de la journée
            end_hour: L'heure de fin de la journée
            
        Returns:
            List[Dict]: Liste des créneaux disponibles avec heure de début et de fin
        """
        # Filtrer les rendez-vous pour la date spécifiée
        date_appointments = [
            appointment for appointment in existing_appointments
            if appointment.start_time.date() == date_to_check
            and appointment.status != AppointmentStatus.CANCELLED
        ]
        
        # Créer des créneaux pour toute la journée
        all_slots = []
        current_time = datetime.combine(date_to_check, datetime.min.time().replace(hour=start_hour))
        end_time = datetime.combine(date_to_check, datetime.min.time().replace(hour=end_hour))
        
        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=slot_duration_minutes)
            all_slots.append({
                "start": current_time,
                "end": slot_end,
                "available": True
            })
            current_time = slot_end
        
        # Marquer les créneaux occupés
        for appointment in date_appointments:
            for slot in all_slots:
                # Si le rendez-vous chevauche le créneau, marquer comme non disponible
                if (appointment.start_time < slot["end"] and appointment.end_time > slot["start"]):
                    slot["available"] = False
        
        # Retourner uniquement les créneaux disponibles
        available_slots = [slot for slot in all_slots if slot["available"]]
        
        return available_slots