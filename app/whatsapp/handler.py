"""
WhatsApp Message Handler
Processes incoming messages and sends agent responses
"""

import logging
import asyncio
from datetime import datetime

from app.whatsapp.client import get_whatsapp_client, WhatsAppMessage
from app.agent.clinic_agent import chat_with_agent

logger = logging.getLogger(__name__)


class WhatsAppHandler:
    """Handles WhatsApp message processing"""
    
    def __init__(self):
        self.client = get_whatsapp_client()
        self.running = False
        logger.info("WhatsApp Handler initialized")
    
    def process_message(self, phone: str, message: str) -> str:
        """Process a single message through the agent"""
        try:
            logger.info(f"Processing message from {phone}: {message[:50]}...")
            
            # Get agent response
            response = chat_with_agent(phone=phone, message=message)
            
            # Send response
            self.client.send_message(phone=phone, message=response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = "Sorry, I encountered an error. Please try again or call the clinic."
            self.client.send_message(phone=phone, message=error_msg)
            return error_msg
    
    def send_confirmation(self, phone: str, appointment_details: dict):
        """Send appointment confirmation"""
        try:
            message = (
                f"✅ Appointment Confirmed\n\n"
                f"Patient: {appointment_details.get('name')}\n"
                f"Date: {appointment_details.get('date')}\n"
                f"Time: {appointment_details.get('time')}\n\n"
                f"Please arrive 10 minutes early.\n"
                f"For cancellation, contact the clinic."
            )
            self.client.send_message(phone=phone, message=message)
            logger.info(f"Confirmation sent to {phone}")
        except Exception as e:
            logger.error(f"Failed to send confirmation: {e}")
    
    def send_reminder(self, phone: str, appointment_details: dict):
        """Send appointment reminder"""
        try:
            message = (
                f"🔔 Appointment Reminder\n\n"
                f"You have an appointment tomorrow:\n"
                f"Date: {appointment_details.get('date')}\n"
                f"Time: {appointment_details.get('time')}\n\n"
                f"Please confirm or call to reschedule."
            )
            self.client.send_message(phone=phone, message=message)
            logger.info(f"Reminder sent to {phone}")
        except Exception as e:
            logger.error(f"Failed to send reminder: {e}")
    
    async def listen_loop(self):
        """
        Listen for incoming messages (for real mode)
        For stub mode, this is not used
        """
        self.running = True
        logger.info("Starting WhatsApp listen loop")
        
        while self.running:
            try:
                # Get new messages
                messages = self.client.get_new_messages()
                
                for msg in messages:
                    # Process each message
                    self.process_message(msg.phone, msg.text)
                
                # Sleep before next poll
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    def stop(self):
        """Stop the listen loop"""
        self.running = False
        logger.info("WhatsApp handler stopped")


# Global handler instance
_handler = None


def get_whatsapp_handler() -> WhatsAppHandler:
    """Get or create global WhatsApp handler"""
    global _handler
    if _handler is None:
        _handler = WhatsAppHandler()
    return _handler
