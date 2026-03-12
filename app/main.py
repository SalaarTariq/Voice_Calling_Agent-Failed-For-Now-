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

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from app.database.db import init_db, get_db_session
from app.database.models import Appointment, Patient
from app.api.routes import router
from app.whatsapp.handler import get_whatsapp_handler


async def send_reminders_loop():
    """Background task: send appointment reminders 24h in advance"""
    logger.info("Reminder service started")

    while True:
        try:
            tomorrow = datetime.now().date() + timedelta(days=1)
            db = get_db_session()
            try:
                appointments = (
                    db.query(Appointment)
                    .join(Patient)
                    .filter(
                        Appointment.date == tomorrow,
                        Appointment.status.in_(["pending", "confirmed"]),
                        Appointment.reminder_sent.is_(None),
                    )
                    .all()
                )

                if appointments:
                    logger.info(f"Sending reminders for {len(appointments)} appointments")
                    handler = get_whatsapp_handler()

                    for apt in appointments:
                        try:
                            details = {
                                "date": apt.date.strftime("%A, %B %d, %Y"),
                                "time": apt.time.strftime("%I:%M %p"),
                                "name": apt.patient.name,
                            }
                            handler.send_reminder(apt.patient.phone, details)
                            apt.reminder_sent = datetime.now()
                            db.commit()
                            logger.info(f"Reminder sent for appointment {apt.id}")
                        except Exception as e:
                            logger.error(f"Reminder failed for appointment {apt.id}: {e}")
                            db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in reminder loop: {e}")

        await asyncio.sleep(3600)  # Check every hour


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    logger.info("Starting AI Clinic Receptionist...")
    init_db()

    reminder_task = asyncio.create_task(send_reminders_loop())

    port = os.getenv("API_PORT", 8000)
    logger.info("=" * 60)
    logger.info("AI Clinic Receptionist is running!")
    logger.info("=" * 60)
    logger.info(f"Dashboard: http://localhost:{port}")
    logger.info(f"API Docs:  http://localhost:{port}/docs")
    logger.info(f"WhatsApp:  {os.getenv('WHATSAPP_MODE', 'stub')}")
    logger.info(f"LLM:       {os.getenv('LLM_PROVIDER', 'gemini')}")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down...")
    reminder_task.cancel()
    try:
        await reminder_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AI Clinic Receptionist",
    description="AI-powered clinic appointment management",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "whatsapp_mode": os.getenv("WHATSAPP_MODE", "stub"),
        "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
    }


def run_console_chat():
    """Interactive console chat for testing"""
    print("=" * 60)
    print("AI Clinic Receptionist - Console Chat")
    print("=" * 60)
    print("Type 'quit' to exit\n")

    init_db()

    handler = get_whatsapp_handler()

    phone = input("Enter your phone number (for session): ").strip()
    if not phone:
        phone = "0300-0000000"

    print(f"\nChatting as: {phone}")
    print("Start by saying: 'I need an appointment'")
    print("-" * 60)

    while True:
        try:
            message = input("\nYou: ").strip()

            if message.lower() in ("quit", "exit", "bye"):
                print("\nGoodbye!")
                break

            if not message:
                continue

            handler.process_message(phone=phone, message=message)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            logger.error(f"Console chat error: {e}", exc_info=True)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="AI Clinic Receptionist")
    parser.add_argument(
        "--mode",
        choices=["server", "console"],
        default="server",
        help="Run mode: server (FastAPI) or console (interactive chat)",
    )
    parser.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", 8000)))

    args = parser.parse_args()

    if args.mode == "console":
        run_console_chat()
    else:
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
        )


if __name__ == "__main__":
    main()
