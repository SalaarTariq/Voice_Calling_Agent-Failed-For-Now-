"""
FastAPI Routes - Simple API for appointments and doctor dashboard
No authentication for MVP
"""

import logging
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.db import get_db
from app.database.models import Appointment, Patient
from app.whatsapp.handler import get_whatsapp_handler

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for API
class AppointmentResponse(BaseModel):
    id: int
    patient_name: str
    patient_phone: str
    patient_age: Optional[int]
    date: str
    time: str
    reason: Optional[str]
    status: str
    created_at: str
    
    class Config:
        from_attributes = True


class AppointmentUpdate(BaseModel):
    status: str  # pending, confirmed, completed, cancelled


# API Endpoints

@router.get("/")
async def serve_dashboard():
    """Serve the doctor dashboard HTML"""
    return FileResponse("static/doctor.html")


@router.get("/api/appointments", response_model=List[AppointmentResponse])
async def get_appointments(
    date_filter: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get all appointments with optional filters"""
    try:
        query = db.query(Appointment).join(Patient)
        
        # Apply filters
        if date_filter:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter(Appointment.date == filter_date)
        
        if status:
            query = query.filter(Appointment.status == status)
        
        # Order by date and time
        appointments = query.order_by(
            Appointment.date.desc(),
            Appointment.time.desc()
        ).all()
        
        # Format response
        result = []
        for apt in appointments:
            result.append(AppointmentResponse(
                id=apt.id,
                patient_name=apt.patient.name,
                patient_phone=apt.patient.phone,
                patient_age=apt.patient.age,
                date=apt.date.strftime("%Y-%m-%d"),
                time=apt.time.strftime("%H:%M"),
                reason=apt.reason,
                status=apt.status,
                created_at=apt.created_at.isoformat()
            ))
        
        return result
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        logger.error(f"Error fetching appointments: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch appointments")


@router.put("/api/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    update:AppointmentUpdate,
    db: Session = Depends(get_db)
):
    """Update appointment status"""
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Update status
        appointment.status = update.status
        db.commit()
        
        logger.info(f"Appointment {appointment_id} updated to {update.status}")
        
        return {"message": "Appointment updated successfully", "id": appointment_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update appointment")


@router.get("/api/appointments/today")
async def get_today_appointments(db: Session = Depends(get_db)):
    """Get today's appointments count"""
    try:
        today = date.today()
        count = db.query(Appointment).filter(Appointment.date == today).count()
        
        pending = db.query(Appointment).filter(
            Appointment.date == today,
            Appointment.status == "pending"
        ).count()
        
        return {
            "total_today": count,
            "pending_today": pending
        }
    except Exception as e:
        logger.error(f"Error fetching today's stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.post("/api/chat")
async def chat_endpoint(phone: str, message: str):
    """
    Chat endpoint for testing via API
    Useful for development without WhatsApp
    """
    try:
        handler = get_whatsapp_handler()
        response = handler.process_message(phone=phone, message=message)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="Failed to process message")
