"""
Main Application Entry Point
Starts FastAPI server with background reminder service
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import app components
from app.database.db import init_db
from app.api.routes import router
from app.whatsapp.handler import get_whatsapp_handler
from app.database.models import Appointment, Patient
from app.database.db import get_db_session


# Background task for sending reminders
async def send_reminders_loop():
    """
    Background task to send appointment reminders
    Checks every hour for appointments in next 24 hours
    """
    logger.info("Starting reminder service...")
    
    while True:
        try:
            # Check appointments for tomorrow
            tomorrow = datetime.now().date() + timedelta(days=1)
            
            db = get_db_session()
            try:
                # Get appointments for tomorrow that haven't had reminders sent
                appointments = db.query(Appointment).join(Patient).filter(
                    Appointment.date == tomorrow,
                    Appointment.status.in_(["pending", "confirmed"]),
                    Appointment.reminder_sent.is_(None)
                ).all()
                
                if appointments:
                    logger.info(f"Found {len(appointments)} appointments needing reminders")
                    
                    handler = get_whatsapp_handler()
                    
                    for apt in appointments:
                        try:
                            # Send reminder
                            details = {
                                "date": apt.date.strftime("%A, %B %d, %Y"),
                                "time": apt.time.strftime("%I:%M %p"),
                                "name": apt.patient.name
                            }
                            
                            handler.send_reminder(apt.patient.phone, details)
                            
                            # Mark reminder as sent
                            apt.reminder_sent = datetime.now()
                            db.commit()
                            
                            logger.info(f"Reminder sent for appointment {apt.id}")
                            
                        except Exception as e:
                            logger.error(f"Failed to send reminder for appointment {apt.id}: {e}")
                            db.rollback()
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in reminder loop: {e}")
        
        # Sleep for 1 hour
        await asyncio.sleep(3600)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting AI Clinic Receptionist...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Start reminder service
    reminder_task = asyncio.create_task(send_reminders_loop())
    logger.info("Reminder service started")
    
    logger.info("=" * 60)
    logger.info("🏥 AI Clinic Receptionist is running!")
    logger.info("=" * 60)
    logger.info(f"Dashboard: http://localhost:{os.getenv('API_PORT', 8000)}")
    logger.info(f"API Docs: http://localhost:{os.getenv('API_PORT', 8000)}/docs")
    logger.info(f"WhatsApp Mode: {os.getenv('WHATSAPP_MODE', 'stub')}")
    logger.info(f"LLM Provider: {os.getenv('LLM_PROVIDER', 'gemini')}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    reminder_task.cancel()
    try:
        await reminder_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Clinic Receptionist",
    description="MVP for automated clinic appointment management",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware (for dashboard)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "whatsapp_mode": os.getenv("WHATSAPP_MODE", "stub"),
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini")
    }


def run_console_chat():
    """
    Run interactive console chat for testing
    Useful for quick testing without WhatsApp
    """
    print("=" * 60)
    print("🏥 AI Clinic Receptionist - Console Chat Mode")
    print("=" * 60)
    print("Type 'quit' to exit\n")
    
    # Initialize database
    init_db()
    
    from app.whatsapp.handler import get_whatsapp_handler
    handler = get_whatsapp_handler()
    
    # Get phone number
    phone = input("Enter your phone number (for memory): ").strip()
    if not phone:
        phone = "0300-0000000"  # Default test number
    
    print(f"\nChatting as: {phone}")
    print("Start by saying: 'I need an appointment'\n")
    print("-" * 60)
    
    while True:
        try:
            # Get user input
            message = input("\nYou: ").strip()
            
            if message.lower() in ["quit", "exit", "bye"]:
                print("\nGoodbye!")
                break
            
            if not message:
                continue
            
            # Process message
            response = handler.process_message(phone=phone, message=message)
            
            # Response is already printed by the stub client
            # Just continue the loop
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            logger.error(f"Console chat error: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Clinic Receptionist")
    parser.add_argument(
        "--mode",
        choices=["server", "console"],
        default="server",
        help="Run mode: server (FastAPI) or console (interactive chat)"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("API_HOST", "0.0.0.0"),
        help="Server host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("API_PORT", 8000)),
        help="Server port"
    )
    
    args = parser.parse_args()
    
    if args.mode == "console":
        # Run console chat
        run_console_chat()
    else:
        # Run FastAPI server
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=False,  # Set to True during development
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )


if __name__ == "__main__":
    main()
