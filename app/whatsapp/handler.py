"""
WhatsApp Message Handler
Routes incoming messages through the AI agent and sends responses
"""

import logging
import asyncio

from app.whatsapp.client import get_whatsapp_client
from app.agent.clinic_agent import chat_with_agent

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """Handles WhatsApp message processing"""

    def __init__(self):
        self.client = get_whatsapp_client()
        self.running = False
        logger.info("WhatsApp Handler initialized")

    def process_message(self, phone: str, message: str) -> str:
        """Process a single message through the AI agent"""
        try:
            logger.info(f"Processing message from {phone}: {message[:50]}...")

            response = chat_with_agent(phone=phone, message=message)
            self.client.send_message(phone=phone, message=response)

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = "Sorry, I encountered an error. Please try again or call the clinic."
            self.client.send_message(phone=phone, message=error_msg)
            return error_msg

    def send_confirmation(self, phone: str, details: dict):
        """Send appointment confirmation"""
        message = (
            "Appointment Confirmed\n\n"
            f"Patient: {details.get('name')}\n"
            f"Date: {details.get('date')}\n"
            f"Time: {details.get('time')}\n\n"
            "Please arrive 10 minutes early.\n"
            "For cancellation, contact the clinic."
        )
        self.client.send_message(phone=phone, message=message)

    def send_reminder(self, phone: str, details: dict):
        """Send appointment reminder (24h before)"""
        message = (
            "Appointment Reminder\n\n"
            f"Dear {details.get('name')}, you have an appointment tomorrow:\n"
            f"Date: {details.get('date')}\n"
            f"Time: {details.get('time')}\n\n"
            "Please confirm or call to reschedule."
        )
        self.client.send_message(phone=phone, message=message)

    async def listen_loop(self):
        """Listen for incoming messages (real WhatsApp mode)"""
        self.running = True
        logger.info("Starting WhatsApp listen loop")

        while self.running:
            try:
                messages = self.client.get_new_messages()
                for msg in messages:
                    self.process_message(msg.phone, msg.text)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(10)

    def stop(self):
        self.running = False


# Global singleton
_handler = None


def get_whatsapp_handler() -> WhatsAppHandler:
    """Get or create global WhatsApp handler"""
    global _handler
    if _handler is None:
        _handler = WhatsAppHandler()
    return _handler
