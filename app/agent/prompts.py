"""
System prompts and urgency detection for AI Clinic Receptionist
Supports English and Roman Urdu
"""

SYSTEM_PROMPT = """You are a clinic receptionist. 
Collect: name, age, phone, reason, date. 
Use tools to check slots and book. 
Concise responses only. Support English and Roman Urdu."""


URGENCY_KEYWORDS = [
    # English
    "chest pain", "heart attack", "can't breathe", "cannot breathe",
    "difficulty breathing", "severe bleeding", "unconscious", "seizure",
    "stroke", "severe pain", "emergency", "dying",
    # Roman Urdu
    "seene mein dard", "dil ka daura", "sans nahi aa rahi",
    "khoon beh raha", "behosh", "bohot dard", "emergency",
    "mar raha", "mar rahi",
]


def is_urgent(text: str) -> bool:
    """Check if message contains urgent/emergency symptoms"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in URGENCY_KEYWORDS)
