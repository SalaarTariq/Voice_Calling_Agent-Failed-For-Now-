"""
AI Clinic Agent - LLM-powered conversational agent using LangChain
Uses tool-calling to check slots and book appointments
"""

import os
import logging
from typing import Dict, List

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.llm.provider import get_llm
from app.agent.tools import CLINIC_TOOLS
from app.agent.prompts import SYSTEM_PROMPT, is_urgent
from app.database.db import get_db_session
from app.database.models import Conversation

logger = logging.getLogger(__name__)

# Per-phone conversation memory (in-memory for MVP)
_conversations: Dict[str, List] = {}

# Lazy-initialized agent
_agent_executor = None


def _get_agent():
    """Lazily create and return the LangChain agent executor"""
    global _agent_executor
    if _agent_executor is not None:
        return _agent_executor

    from langgraph.prebuilt import create_react_agent

    llm = get_llm()
    _agent_executor = create_react_agent(llm, CLINIC_TOOLS, prompt=SYSTEM_PROMPT)

    logger.info("LangChain ReAct agent initialized")
    return _agent_executor


def _get_history(phone: str) -> List:
    """Get or create message history for a phone number"""
    if phone not in _conversations:
        _conversations[phone] = []
    return _conversations[phone]


def chat_with_agent(phone: str, message: str) -> str:
    """
    Process a patient message and return the agent's response.

    Args:
        phone: Patient's phone number (used as session key)
        message: The patient's message text

    Returns:
        The agent's response string
    """
    try:
        # Check for emergency keywords first
        if is_urgent(message):
            response = (
                "URGENT: Based on your symptoms, this may be an emergency. "
                "Please call emergency services (115) or go to the nearest hospital immediately. "
                "Do not wait for an appointment."
            )
            _save_conversation(phone, f"Patient: {message}\nAgent: {response}")
            return response

        # Build messages for the agent
        history = _get_history(phone)
        history.append(HumanMessage(content=message))

        agent = _get_agent()

        # Invoke the agent with full conversation history
        result = agent.invoke({"messages": history})

        # Extract the assistant's final response
        response_messages = result.get("messages", [])
        ai_response = ""
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                ai_response = msg.content
                break

        if not ai_response:
            ai_response = "I'm sorry, I couldn't process that. Could you please try again?"

        # Update history with the AI response
        history.append(AIMessage(content=ai_response))

        # Keep history manageable (last 20 messages)
        if len(history) > 20:
            _conversations[phone] = history[-20:]

        # Persist to database
        _save_conversation(phone, f"Patient: {message}\nAgent: {ai_response}")

        # Send doctor notification if an appointment was just booked
        _check_and_notify_doctor(response_messages, phone)

        return ai_response

    except Exception as e:
        logger.error(f"Error in chat_with_agent: {e}", exc_info=True)
        return "I'm sorry, I encountered an error. Please try again or contact the clinic directly."


def _check_and_notify_doctor(messages: list, phone: str):
    """Check if an appointment was booked and notify the doctor"""
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg.content, str):
            if "Appointment confirmed!" in msg.content:
                try:
                    _send_doctor_notification(msg.content, phone)
                except Exception as e:
                    logger.error(f"Failed to send doctor notification: {e}")
                break


def _send_doctor_notification(booking_details: str, patient_phone: str):
    """Send appointment notification to doctor's WhatsApp"""
    from app.whatsapp.client import get_whatsapp_client

    doctor_whatsapp = os.getenv("PERSONAL_WHATSAPP", "")
    if not doctor_whatsapp:
        return

    notification = (
        "NEW APPOINTMENT BOOKED\n\n"
        f"{booking_details}\n\n"
        "---\n"
        "AI Clinic Receptionist"
    )

    client = get_whatsapp_client()
    client.send_message(doctor_whatsapp, notification)
    logger.info("Doctor notification sent")


def _save_conversation(phone: str, transcript: str):
    """Save conversation turn to database"""
    try:
        db = get_db_session()
        try:
            from app.database.models import Patient
            patient = db.query(Patient).filter(Patient.phone == phone).first()

            conversation = Conversation(
                patient_id=patient.id if patient else None,
                phone=phone,
                transcript=transcript,
            )
            db.add(conversation)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")


def clear_memory(phone: str):
    """Clear conversation memory for a phone number"""
    if phone in _conversations:
        del _conversations[phone]
        logger.info(f"Cleared memory for {phone}")
