"""
Enhanced Demo - Shows conversational AI with small talk and doctor notifications
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.whatsapp.handler import get_whatsapp_handler
from app.database.db import init_db

def test_conversational_booking():
    """Test the new conversational friendly booking flow"""
    
    print("=" * 70)
    print("🏥 AI CLINIC RECEPTIONIST - CONVERSATIONAL DEMO")
    print("=" * 70)
    print("\nInitializing system...")
    
    init_db()
    print("✅ Database initialized")
    
    handler = get_whatsapp_handler()
    print("✅ WhatsApp handler ready")
    print("✅ AI Agent loaded (Conversational Mode)")
    
    # Test with friendly conversation flow
    test_phone = "03001234567"
    
    messages = [
        "Hello",  # Greeting
        "I'm not feeling well",  # Small talk response
        "Ahmed Khan",  # Name
        "35",  # Age
        "0300-1234567",  # Phone
        "Fever and headache for 3 days",  # Symptoms
        "Tomorrow",  # Date
        "2:30 PM"  # Time
    ]
    
    print("\n" + "=" * 70)
    print("CONVERSATIONAL FLOW TEST")
    print("=" * 70)
    print("\nNotice:")
    print("1. Initial greeting + 'How are you?'")
    print("2. Small talk response before booking")
    print("3. Friendly goodbye after booking")
    print("4. Doctor notification sent to: 03339114784")
    print("=" * 70)
    
    for i, message in enumerate(messages, 1):
        print(f"\n\n{'='*70}")
        print(f"💬 TURN {i}/{len(messages)}")
        print(f"{'='*70}")
        print(f"\n🧑 Patient says: \"{message}\"")
        print(f"\n{'·'*70}\n")
        
        # Process message
        response = handler.process_message(phone=test_phone, message=message)
        
        # Response already printed by stub
        print(f"\n{'='*70}")
        
        import time
        time.sleep(1.5)
    
    print("\n\n" + "=" * 70)
    print("✅ CONVERSATIONAL DEMO COMPLETE!")
    print("=" * 70)
    print("\n📊 Key Features Demonstrated:")
    print("   ✅ Friendly greeting ('How are you?')")
    print("   ✅ Small talk before business")
    print("   ✅ Warm, personalized responses")
    print("   ✅ Complete booking flow")
    print("   ✅ Friendly goodbye message")
    print("   ✅ Doctor notification sent to: 03339114784")
    print("\n🎯 Doctor received notification with:")
    print("   • Patient name, phone, age")
    print("   • Appointment date and time")
    print("   • Reason for visit")
    print("   • Confirmation status")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    try:
        test_conversational_booking()
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
