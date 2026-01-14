"""
AI Clinic Agent - Simplified conversational agent
Fixed for LangChain 0.1.4 compatibility
"""

import logging
from typing import Dict
from datetime import datetime, timedelta

from app.llm.provider import get_llm
from app.agent.tools import get_available_slots, book_appointment, get_patient_history
from app.agent.prompts import SYSTEM_PROMPT, is_urgent
from app.database.db import get_db_session
from app.database.models import Conversation

logger = logging.getLogger(__name__)

# Store conversation state for each phone number
conversation_states: Dict[str, Dict] = {}


def get_conversation_state(phone: str) -> Dict:
    """Get or create conversation state for a phone number"""
    if phone not in conversation_states:
        conversation_states[phone] = {
            "messages": [],
            "context": {}
        }
    return conversation_states[phone]


def chat_with_agent(phone: str, message: str) -> str:
    """
    Process a message through a simple conversational flow
    
    Args:
        phone: Patient's phone number
        message: User's message
        
    Returns:
        Agent's response
    """
    try:
        # Get conversation state
        state = get_conversation_state(phone)
        
        # Add user message to history
        state["messages"].append({"role": "user", "content": message})
        
        # Check for urgency
        if is_urgent(message):
            response = ("⚠️ URGENT: Based on your symptoms, this may be an emergency. "
                       "Please call emergency services (115) or go to the nearest hospital immediately. "
                       "Do not wait for an appointment.")
            state["messages"].append({"role": "assistant", "content": response})
            save_conversation(phone, f"Patient: {message}\\nAgent: {response}")
            return response
        
        # Build context from previous messages
        context = state.get("context", {})
        
        # Extract information from current message (simple keyword matching for MVP)
        extract_patient_info(message, context)
        state["context"] = context
        
        # Determine next step based on collected information
        response = generate_response(phone, context, message, state["messages"])
        
        # Add assistant message to history
        state["messages"].append({"role": "assistant", "content": response})
        
        # Save to database
        save_conversation(phone, f"Patient: {message}\\nAgent: {response}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat_with_agent: {e}", exc_info=True)
        return "I'm sorry, I encountered an error. Please try again or contact the clinic directly."


def extract_patient_info(message: str, context: Dict):
    """Extract patient information from message using simple patterns"""
    message_lower = message.lower()
    
    # Extract age
    import re
    age_match = re.search(r'(\d{1,3})\s*(?:years?|saal|sal|old)', message_lower)
    if age_match and 'age' not in context:
        context['age'] = int(age_match.group(1))
    # Also check standalone numbers that could be age (between 1-120)
    elif 'age' not in context and 'name' in context:
        num_match = re.search(r'\b(\d{1,3})\b', message)
        if num_match:
            age_val = int(num_match.group(1))
            if 1 <= age_val <= 120:
                context['age'] = age_val
    
    # Extract phone (Pakistan format)
    phone_match = re.search(r'03\d{2}[- ]?\d{7}', message)
    if phone_match and'phone' not in context:
        context['phone'] = phone_match.group(0).replace(' ', '').replace('-', '')
    
    # Check for name - improved detection
    if 'name' not in context:
        # Check if message starts with "my name is" or similar
        name_patterns = [
            r'(?:my name is|i am|this is|naam hai|mera naam)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$',  # Just a capitalized name
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                context['name'] = match.group(1).title()
                break
        
        # If no pattern match but looks like a name (2-4 capitalized words, no numbers)
        if 'name' not in context:
            words = message.split()
            if 2 <= len(words) <= 4 and not re.search(r'\d', message):
                # Check if not a question or command
                question_words = ['what', 'when', 'where', 'how', 'why', 'need', 'want', 'appointment', 'doctor', 'help', 'please']
                if not any(word in message_lower for word in question_words):
                    context['name'] = ' '.join([w.capitalize() for w in words])
    
    # Check for symptoms/reasons
    symptom_keywords = ['pain', 'dard', 'fever', 'bukhar', 'cough', 'khansi', 'headache', 'sar dard', 'checkup', 'sick', 'bimar', 'body pain']
    if any(keyword in message_lower for keyword in symptom_keywords) and 'reason' not in context:
        context['reason'] = message
    
    # Date extraction (tomorrow, specific dates)
    if 'tomorrow' in message_lower or 'kal' in message_lower:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        context['date'] = tomorrow
    elif 'today' in message_lower or 'aaj' in message_lower:
        context['date'] = datetime.now().strftime("%Y-%m-%d")


def generate_response(phone: str, context: Dict, message: str, history: list) -> str:
    """Generate appropriate response based on conversation state"""
    
    # Track conversation stage
    conversation_stage = context.get('stage', 'greeting')
    
    # STAGE 1: Initial greeting and small talk
    if conversation_stage == 'greeting' or len(history) <= 2:
        # Friendly greeting
        if any(word in message.lower() for word in ['hello', 'hi', 'assalam', 'salam', 'hey']):
            context['stage'] = 'small_talk'
            return ("Hello! Welcome to our clinic. It's great to hear from you! 😊\n\n"
                   "How are you doing today?")
        else:
            context['stage'] = 'small_talk'
            return "Hello! Welcome to our clinic. How are you doing today?"
    
    # STAGE 2: Respond to small talk, then transition
    if conversation_stage == 'small_talk':
        # Acknowledge their response warmly
        responses = [
            "That's good to hear! I'm glad you reached out to us. 😊",
            "I'm sorry to hear that. Don't worry, we're here to help you!",
            "Thank you for sharing! We'll take good care of you.",
        ]
        
        # Detect sentiment
        if any(word in message.lower() for word in ['good', 'fine', 'great', 'okay', 'theek', 'acha']):
            response = "That's wonderful! I'm glad you're doing well. 😊\n\n"
        elif any(word in message.lower() for word in ['not good', 'sick', 'unwell', 'pain', 'bad', 'bimar']):
            response = "I'm sorry to hear you're not feeling well. We're here to help you! 🏥\n\n"
        else:
            response = "Thank you for reaching out to us! 😊\n\n"
        
        context['stage'] = 'booking'
        return response + "I can help you book an appointment with our doctor. May I have your name please?"
    
    # STAGE 3: Booking process - collect information
    if conversation_stage == 'booking':
        # Check what information we still need
        needed = []
        if 'name' not in context:
            needed.append('name')
        if 'age' not in context:
            needed.append('age')
        if 'phone' not in context:
            needed.append('phone')
        if 'reason' not in context:
            needed.append('reason')
        if 'date' not in context:
            needed.append('date')
        
        # Ask for next missing piece of information
        if needed:
            next_field = needed[0]
            
            if next_field == 'name':
                return "May I have your name please?"
            elif next_field == 'age':
                return f"Thank you, {context.get('name', '')}! What is your age?"
            elif next_field == 'phone':
                return "Great! What is your phone number?"
            elif next_field == 'reason':
                return "I understand. What is the main health concern you'd like to see the doctor for?"
            elif next_field == 'date':
                return "Got it. Which date would you prefer for your appointment?"
        
        # If we have date but no time selected, show available slots
        if 'date' in context and 'time' not in context and not context.get('shown_slots'):
            slots_result = get_available_slots(context['date'])
            context['shown_slots'] = True
            return slots_result + "\n\nWhich time works best for you?"
    
    # STAGE 4: Time selection and booking
    # Check if message contains time selection
    import re
    time_patterns = [
        r'(\d{1,2}):?(\d{2})?\s*(am|pm|AM|PM)?',
        r'(\d{1,2})\s*(am|pm|AM|PM)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, message)
        if match and 'time' not in context:
            # Parse time
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            meridiem = match.group(3).lower() if match.group(3) else None
            
            # Convert to 24-hour format
            if meridiem == 'pm' and hour < 12:
                hour += 12
            elif meridiem == 'am' and hour == 12:
                hour = 0
            
            time_str = f"{hour:02d}:{minute:02d}"
            context['time'] = time_str
            
            # Book appointment - inline to avoid import issues
            try:
                from datetime import datetime as dt
                from app.database.models import Patient, Appointment
                from app.database.db import get_db_session
                
                target_date = dt.strptime(context['date'], "%Y-%m-%d").date()
                target_time = dt.strptime(time_str, "%H:%M").time()
                
                db = get_db_session()
                try:
                    patient = db.query(Patient).filter(Patient.phone == context.get('phone', phone)).first()
                    if not patient:
                        patient = Patient(
                            name=context.get('name', 'Unknown'),
                            phone=context.get('phone', phone),
                            age=context.get('age', 0)
                        )
                        db.add(patient)
                        db.flush()
                    
                    appointment = Appointment(
                        patient_id=patient.id,
                        date=target_date,
                        time=target_time,
                        reason=context.get('reason', 'General consultation'),
                        status="confirmed"
                    )
                    db.add(appointment)
                    db.commit()
                    
                    friendly_time = target_time.strftime("%I:%M %p")
                    friendly_date = target_date.strftime("%A, %B %d, %Y")
                    
                    booking_result = (f"✅ Appointment confirmed!\n\n"
                                    f"Patient: {context.get('name')}\n"
                                    f"Date: {friendly_date}\n"
                                    f"Time: {friendly_time}\n"
                                    f"Phone: {context.get('phone', phone)}")
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Booking error: {e}")
                booking_result = "Sorry, there was an error booking your appointment."
            
            # SEND NOTIFICATION TO DOCTOR
            send_doctor_notification(
                patient_name=context.get('name', 'Unknown'),
                patient_phone=context.get('phone', phone),
                patient_age=context.get('age', 0),
                appointment_date=context['date'],
                appointment_time=time_str,
                reason=context.get('reason', 'General consultation')
            )
            
            # Add friendly goodbye
            goodbye_msg = ("\n\n" + booking_result + "\n\n" +
                          "Thank you for choosing our clinic! We look forward to seeing you. "
                          "If you have any questions before your appointment, feel free to reach out. "
                          "Take care and get well soon! 🏥😊\n\n"
                          "Have a great day!")
            
            # Clear context after booking
            conversation_states[phone] = {'messages': [], 'context': {}}
            
            return goodbye_msg
    
    # If all info collected but still no booking, prompt for time
    if context.get('shown_slots') and 'time' not in context:
        return "Please let me know which time slot you'd like. For example, say '2:00 PM' or '10:30 AM'"
    
    # Default: friendly response
    return "I'd be happy to help! Could you please provide the information I asked for?"


def send_doctor_notification(patient_name: str, patient_phone: str, patient_age: int,
                             appointment_date: str, appointment_time: str, reason: str):
    """Send appointment notification to doctor's WhatsApp"""
    try:
        import os
        from app.whatsapp.client import get_whatsapp_client
        from datetime import datetime
        
        # Doctor's WhatsApp number from environment
        doctor_whatsapp = os.getenv("PERSONAL_WHATSAPP", "03339114784")
        
        # Format the notification message
        # Parse date for friendly format
        try:
            date_obj = datetime.strptime(appointment_date, "%Y-%m-%d")
            friendly_date = date_obj.strftime("%A, %B %d, %Y")
        except:
            friendly_date = appointment_date
        
        # Parse time for friendly format
        try:
            time_parts = appointment_time.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            period = "AM" if hour < 12 else "PM"
            hour_12 = hour if hour <= 12 else hour - 12
            if hour_12 == 0:
                hour_12 = 12
            friendly_time = f"{hour_12}:{minute:02d} {period}"
        except:
            friendly_time = appointment_time
        
        notification = f"""🏥 NEW APPOINTMENT BOOKED

👤 Patient: {patient_name}
📞 Phone: {patient_phone}
🎂 Age: {patient_age} years
📅 Date: {friendly_date}
🕐 Time: {friendly_time}
💊 Reason: {reason}

━━━━━━━━━━━━━━━━━━━━
Status: Confirmed ✅
System: AI Clinic Receptionist"""
        
        # Send notification
        client = get_whatsapp_client()
        client.send_message(doctor_whatsapp, notification)
        
        logger.info(f"Doctor notification sent for appointment: {patient_name}")
        
    except Exception as e:
        logger.error(f"Failed to send doctor notification: {e}")
        # Don't fail the booking if notification fails


def save_conversation(phone: str, transcript: str):
    """Save conversation to database"""
    try:
        db = get_db_session()
        try:
            from app.database.models import Patient
            patient = db.query(Patient).filter(Patient.phone == phone).first()
            patient_id = patient.id if patient else None
            
            conversation = Conversation(
                patient_id=patient_id,
                phone=phone,
                transcript=transcript
            )
            db.add(conversation)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")


def clear_memory(phone: str):
    """Clear conversation memory for a phone number"""
    if phone in conversation_states:
        del conversation_states[phone]
        logger.info(f"Cleared memory for {phone}")
