"""
Agent tools for database operations and appointment management
Hardcoded clinic hours: 10am-8pm, 30-minute slots
"""

import os
import logging
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Dict
from langchain.tools import tool
from sqlalchemy.orm import Session

from app.database.models import Patient, Appointment, Conversation
from app.database.db import get_db_session
from app.agent.prompts import is_urgent

logger = logging.getLogger(__name__)

# Hardcoded clinic settings from environment (with defaults)
CLINIC_START_HOUR = int(os.getenv("CLINIC_START_HOUR", "10"))
CLINIC_END_HOUR = int(os.getenv("CLINIC_END_HOUR", "20"))
SLOT_DURATION_MINUTES = int(os.getenv("SLOT_DURATION_MINUTES", "30"))


def generate_time_slots() -> List[time]:
    """Generate all possible appointment slots for a day"""
    slots = []
    current_hour = CLINIC_START_HOUR
    current_minute = 0
    
    while current_hour < CLINIC_END_HOUR:
        slots.append(time(hour=current_hour, minute=current_minute))
        
        # Add slot duration
        current_minute += SLOT_DURATION_MINUTES
        if current_minute >= 60:
            current_hour += 1
            current_minute = 0
    
    return slots


@tool
def get_available_slots(appointment_date: str) -> str:
    """
    Get available appointment slots for a given date.
    
    Args:
        appointment_date: Date in YYYY-MM-DD format
        
    Returns:
        String listing available time slots
    """
    try:
        # Parse date
        target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        
        # Don't allow past dates
        if target_date < date.today():
            return "Sorry, I cannot book appointments for past dates. Please choose today or a future date."
        
        # Get all possible slots
        all_slots = generate_time_slots()
        
        # Query booked slots for this date
        db = get_db_session()
        try:
            booked_appointments = db.query(Appointment).filter(
                Appointment.date == target_date,
                Appointment.status.in_(["pending", "confirmed"])
            ).all()
            
            booked_times = {apt.time for apt in booked_appointments}
            
            # Filter available slots
            available = [slot for slot in all_slots if slot not in booked_times]
            
            if not available:
                return f"Sorry, no slots available on {appointment_date}. Please try another date."
            
            # Format response
            slot_strings = [slot.strftime("%I:%M %p") for slot in available]
            return f"Available slots on {appointment_date}: {', '.join(slot_strings)}"
            
        finally:
            db.close()
            
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-01-15)"
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return "Sorry, I encountered an error checking availability. Please try again."


@tool
def book_appointment(name: str, phone: str, age: int, appointment_date: str, appointment_time: str, reason: str) -> str:
    """
    Book an appointment for a patient.
    
    Args:
        name: Patient's full name
        phone: Patient's phone number
        age: Patient's age
        appointment_date: Date in YYYY-MM-DD format
        appointment_time: Time in HH:MM format (24-hour)
        reason: Reason for visit/symptoms
        
    Returns:
        Confirmation message
    """
    try:
        # Check for urgency first
        if is_urgent(reason):
            return ("⚠️ URGENT: Based on your symptoms, this may be an emergency. "
                   "Please call emergency services (115) or go to the nearest hospital immediately. "
                   "Do not wait for an appointment.")
        
        # Parse date and time
        target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        target_time = datetime.strptime(appointment_time, "%H:%M").time()
        
        db = get_db_session()
        try:
            # Check if patient exists
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            
            if not patient:
                # Create new patient
                patient = Patient(name=name, phone=phone, age=age)
                db.add(patient)
                db.flush()  # Get patient ID
            
            # Check if slot is still available
            existing = db.query(Appointment).filter(
                Appointment.date == target_date,
                Appointment.time == target_time,
                Appointment.status.in_(["pending", "confirmed"])
            ).first()
            
            if existing:
                return f"Sorry, the slot at {appointment_time} on {appointment_date} was just booked. Please choose another time."
            
            # Create appointment
            appointment = Appointment(
                patient_id=patient.id,
                date=target_date,
                time=target_time,
                reason=reason,
                status="confirmed"
            )
            db.add(appointment)
            db.commit()
            
            # Format friendly time
            friendly_time = target_time.strftime("%I:%M %p")
            friendly_date = target_date.strftime("%A, %B %d, %Y")
            
            return (f"✅ Appointment confirmed!\n\n"
                   f"Patient: {name}\n"
                   f"Date: {friendly_date}\n"
                   f"Time: {friendly_time}\n"
                   f"Phone: {phone}\n\n"
                   f"You will receive a reminder message before your appointment. "
                   f"Please arrive 10 minutes early. Thank you!")
            
        finally:
            db.close()
            
    except ValueError as e:
        return f"Invalid date or time format. Please provide date as YYYY-MM-DD and time as HH:MM"
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return "Sorry, I encountered an error while booking. Please try again or contact the clinic directly."


@tool
def get_patient_history(phone: str) -> str:
    """
    Get patient's appointment history.
    
    Args:
        phone: Patient's phone number
        
    Returns:
        Patient's appointment history
    """
    try:
        db = get_db_session()
        try:
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            
            if not patient:
                return "No previous appointments found for this number."
            
            appointments = db.query(Appointment).filter(
                Appointment.patient_id == patient.id
            ).order_by(Appointment.date.desc()).limit(5).all()
            
            if not appointments:
                return f"Welcome back, {patient.name}! You don't have any previous appointments."
            
            history = [f"Patient: {patient.name}, Age: {patient.age}"]
            history.append("\nRecent appointments:")
            
            for apt in appointments:
                history.append(
                    f"- {apt.date} at {apt.time.strftime('%I:%M %p')}: "
                    f"{apt.reason} ({apt.status})"
                )
            
            return "\n".join(history)
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error getting patient history: {e}")
        return "Unable to retrieve patient history at this time."


# List all tools for easy import
CLINIC_TOOLS = [
    get_available_slots,
    book_appointment,
    get_patient_history,
]

def book_appointment_direct(name, phone, age, appointment_date, appointment_time, reason):
    """Direct booking - non-tool version"""
    from app.database.models import Patient, Appointment
    from app.database.db import get_db_session
    from datetime import datetime
    
    try:
        target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        target_time = datetime.strptime(appointment_time, "%H:%M").time()
        
        db = get_db_session()
        try:
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            if not patient:
                patient = Patient(name=name, phone=phone, age=age)
                db.add(patient)
                db.flush()
            
            appointment = Appointment(
                patient_id=patient.id,
                date=target_date,
                time=target_time,
                reason=reason,
                status="confirmed"
            )
            db.add(appointment)
            db.commit()
            
            friendly_time = target_time.strftime("% I:%M %p")
            friendly_date = target_date.strftime("%A, %B %d, %Y")
            
            return f"✅ Appointment confirmed!\n\nPatient: {name}\nDate: {friendly_date}\nTime: {friendly_time}\nPhone: {phone}"
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error: {e}")
        return "Sorry, error while booking."
