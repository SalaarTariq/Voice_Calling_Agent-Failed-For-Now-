"""
Agent tools for appointment management
FIXED: 
1. Past dates booking validation
2. Out-of-office hours validation
3. Non-standard time slots (Bug №3 - slot granularity)
4. Race Condition (Integrity check for concurrent bookings)
"""

import os
import logging
from datetime import datetime, date, time
from typing import List
from sqlalchemy.exc import IntegrityError
from langchain_core.tools import tool

from app.database.models import Patient, Appointment
from app.database.db import get_db_session

logger = logging.getLogger(__name__)

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
    """
    try:
        target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()

        if target_date < date.today():
            return "Sorry, cannot book appointments for past dates. Please choose today or a future date."

        all_slots = generate_time_slots()

        db = get_db_session()
        try:
            booked = db.query(Appointment).filter(
                Appointment.date == target_date,
                Appointment.status.in_(["pending", "confirmed"]),
            ).all()
            booked_times = {apt.time for apt in booked}
            available = [s for s in all_slots if s not in booked_times]

            if not available:
                return f"No slots available on {appointment_date}. Please try another date."

            slot_strings = [s.strftime("%I:%M %p") for s in available]
            return f"Available slots on {appointment_date}:\n" + "\n".join(slot_strings)
        finally:
            db.close()

    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD (e.g., 2024-01-15)"
    except Exception as e:
        logger.error(f"Error getting available slots: {e}")
        return "Sorry, error checking availability."


@tool
def book_appointment(name: str, phone: str, age: int, appointment_date: str, appointment_time: str, reason: str) -> str:
    """
    Book an appointment for a patient. Call this once you have ALL required details.
    """
    try:
        target_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
        target_time = datetime.strptime(appointment_time, "%H:%M").time()

        # --- FIX 1: Prevent booking in the past ---
        if target_date < date.today():
            return f"Error: Cannot book for a past date ({appointment_date})."

        # --- FIX 2 & 3: Validate against clinic hours and slot granularity ---
        valid_slots = generate_time_slots()
        if target_time not in valid_slots:
            # UX Improvement: Suggest using the availability tool
            return (f"Error: {appointment_time} is not a valid slot. "
                    f"Please use get_available_slots to see the standard {SLOT_DURATION_MINUTES}-minute "
                    f"slots available between {CLINIC_START_HOUR}:00 and {CLINIC_END_HOUR}:00.")

        db = get_db_session()
        try:
            # Handle patient record
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            if not patient:
                patient = Patient(name=name, phone=phone, age=age)
                db.add(patient)
                db.flush()

            # --- FIX 4: Handle Race Condition via Atomic Database Commit ---
            # REQUIRES: UniqueConstraint('date', 'time') in Appointment model
            new_appointment = Appointment(
                patient_id=patient.id,
                date=target_date,
                time=target_time,
                reason=reason,
                status="confirmed",
            )
            db.add(new_appointment)
            db.commit()

            friendly_time = target_time.strftime("%I:%M %p")
            friendly_date = target_date.strftime("%A, %B %d, %Y")

            return (
                f"Appointment confirmed!\n\n"
                f"Patient: {name}\n"
                f"Date: {friendly_date}\n"
                f"Time: {friendly_time}\n"
                f"Phone: {phone}\n\n"
                f"Please arrive 10 minutes early."
            )

        except IntegrityError:
            db.rollback()
            return f"Conflict: The slot {appointment_time} on {appointment_date} was just taken. Please use get_available_slots to find another time."
        finally:
            db.close()

    except ValueError:
        return "Invalid date or time format. Date: YYYY-MM-DD, Time: HH:MM (24h format)"
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        return "Sorry, internal error while booking. Please try again."


@tool
def get_patient_history(phone: str) -> str:
    """
    Look up a patient's previous appointments by phone number.
    """
    try:
        db = get_db_session()
        try:
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            if not patient:
                return "No previous records found for this phone number."

            appointments = (
                db.query(Appointment)
                .filter(Appointment.patient_id == patient.id)
                .order_by(Appointment.date.desc())
                .limit(5)
                .all()
            )

            if not appointments:
                return f"Welcome back, {patient.name}! No previous appointments on file."

            lines = [f"Patient: {patient.name}, Age: {patient.age}", "\nRecent appointments:"]
            for apt in appointments:
                lines.append(
                    f"- {apt.date} at {apt.time.strftime('%I:%M %p')}: {apt.reason} ({apt.status})"
                )
            return "\n".join(lines)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error getting patient history: {e}")
        return "Unable to retrieve patient history at this time."


CLINIC_TOOLS = [get_available_slots, book_appointment, get_patient_history]
