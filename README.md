# AI Clinic Receptionist - MVP

A **lean, production-ready MVP** of an AI-powered medical clinic receptionist for clinics in Pakistan. Handles patient interactions via WhatsApp, books appointments, and provides a doctor dashboard—all using **free and open-source tools**.

## ✨ Features

- 🤖 **AI-Powered Conversations**: LangChain agent with Gemini or Groq LLM
- 💬 **Bilingual Support**: English and Roman Urdu (e.g., "appointment chahiye")
- 📱 **WhatsApp Integration**: Console stub + real WhatsApp Web automation
- 📅 **Appointment Management**: Auto-booking with slot availability checks
- 🏥 **Doctor Dashboard**: Real-time appointment view with status updates
- ⚠️ **Urgency Detection**: Identifies emergency symptoms and escalates
- 🔔 **Auto Reminders**: 24-hour advance WhatsApp reminders
- 💾 **SQLite Database**: Simple, embedded database (upgrade to PostgreSQL later)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or uv (recommended)
- Git (for cloning)

### Installation

1. **Clone the repository**
   ```bash
   cd /Volumes/Drive\ D/Calling_Chatbot
   cd AI_CLINIC_RECEPTIONIST
   ```

2. **Install dependencies**
   
   **Option A: Using pip**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
   
   **Option B: Using uv (faster)**
   ```bash
   # Install uv if not already installed
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Create virtual environment and install
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```
   
   **Required environment variables:**
   ```bash
   # Get a free Gemini API key from: https://makersuite.google.com/app/apikey
   # OR get a free Groq API key from: https://console.groq.com
   
   LLM_PROVIDER=gemini  # or "groq"
   GEMINI_API_KEY=your_key_here
   GROQ_API_KEY=your_key_here  # (if using Groq)
   
   WHATSAPP_MODE=stub  # Use "stub" for console testing
   ```

4. **Run the application**
   ```bash
   python app/main.py
   ```
   
   The server will start at: **http://localhost:8000**

---

## 📖 Usage

### Testing with Console Mode

Perfect for testing without WhatsApp:

```bash
python app/main.py --mode console
```

This opens an interactive chat where you can test the AI agent:

```
Enter your phone number (for memory): 0300-1234567
Chatting as: 0300-1234567
Start by saying: 'I need an appointment'
------------------------------------------------------------

You: I need an appointment
Agent: I'd be happy to help you book an appointment. May I have your name please?

You: My name is Ali
Agent: Nice to meet you, Ali! May I know your age?

You: 25
Agent: Thank you. What is your phone number?

You: 0300-1234567
Agent: Got it. What is the main health concern you'd like to see the doctor for?

You: Fever and headache
Agent: I understand. Which date would you prefer for your appointment?

You: tomorrow
Agent: Let me check available slots for tomorrow...
```

### Using the Doctor Dashboard

1. Open http://localhost:8000 in your browser
2. View all appointments in real-time
3. Filter by date or status
4. Mark appointments as completed or cancelled
5. Auto-refreshes every 30 seconds

### Using Real WhatsApp Mode

1. Change `.env`: `WHATSAPP_MODE=real`
2. Run: `python app/main.py`
3. **First time only**: Scan QR code in the browser window that opens
4. Send messages to the clinic's WhatsApp number
5. AI responds automatically

**Note**: WhatsApp Web mode is not production-grade. For production, use the official WhatsApp Business API (paid).

---

## 🏗️ Project Structure

```
AI_CLINIC_RECEPTIONIST/
├── app/
│   ├── agent/              # AI agent logic
│   │   ├── clinic_agent.py # Main LangChain agent
│   │   ├── prompts.py      # System prompts
│   │   └── tools.py        # Agent tools (DB operations)
│   ├── api/
│   │   └── routes.py       # FastAPI endpoints
│   ├── database/
│   │   ├── db.py           # Database setup
│   │   └── models.py       # SQLAlchemy models
│   ├── llm/
│   │   └── provider.py     # LLM factory (Gemini/Groq)
│   ├── speech/             # Optional STT/TTS
│   │   ├── stt.py          # Whisper
│   │   └── tts.py          # gTTS
│   ├── whatsapp/
│   │   ├── client.py       # WhatsApp client
│   │   └── handler.py      # Message handler
│   └── main.py             # Entry point
├── static/
│   └── doctor.html         # Dashboard UI
├── .env.example            # Environment template
├── requirements.txt        # Dependencies
└── README.md              # This file
```

---

## 🔧 Configuration

### Clinic Hours (Hardcoded)

Edit `.env` to change:
```bash
CLINIC_START_HOUR=10    # 10 AM
CLINIC_END_HOUR=20      # 8 PM
SLOT_DURATION_MINUTES=30
```

Or modify directly in `app/agent/tools.py` for custom logic.

### Database

Default: `clinic.db` in the project root.

To use a different location:
```bash
DATABASE_URL=sqlite:///path/to/your/database.db
```

For production, upgrade to PostgreSQL:
```bash
DATABASE_URL=postgresql://user:password@localhost/dbname
```

---

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Doctor dashboard (HTML) |
| `/api/appointments` | GET | List appointments (with filters) |
| `/api/appointments/{id}` | PUT | Update appointment status |
| `/api/appointments/today` | GET | Today's stats |
| `/api/chat` | POST | Test chat endpoint |
| `/health` | GET | Health check |
| `/docs` | GET | Auto-generated API docs |

### Example API Usage

**Get all appointments:**
```bash
curl http://localhost:8000/api/appointments
```

**Get appointments for a specific date:**
```bash
curl "http://localhost:8000/api/appointments?date_filter=2024-01-15"
```

**Update appointment status:**
```bash
curl -X PUT http://localhost:8000/api/appointments/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

**Test chat (without WhatsApp):**
```bash
curl -X POST "http://localhost:8000/api/chat?phone=0300-1234567&message=I need an appointment"
```

---

## 💬 Conversation Examples

### English Conversation

```
Patient: Hello
Agent: Hello! Welcome to our clinic. How may I help you today?

Patient: I need to see a doctor
Agent: I'd be happy to help you book an appointment. May I have your name please?

Patient: Sarah Ahmed
Agent: Nice to meet you, Sarah! May I know your age?

Patient: 30
Agent: Thank you. What is your phone number?

Patient: 0321-5555555
Agent: Got it. What is the main health concern you'd like to see the doctor for?

Patient: Regular checkup
Agent: I understand. Which date would you prefer for your appointment?

Patient: January 20, 2024
Agent: Let me check available slots for 2024-01-20...
Available slots: 10:00 AM, 10:30 AM, 11:00 AM, 11:30 AM, 12:00 PM, ...

Patient: 2pm please
Agent: ✅ Appointment confirmed!

Patient: Sarah Ahmed
Date: Saturday, January 20, 2024
Time: 02:00 PM
Phone: 0321-5555555

You will receive a reminder message before your appointment.
```

### Roman Urdu Conversation

```
Patient: Assalam o Alaikum
Agent: Walaikum Assalam! Kaise madad kar sakta hoon?

Patient: Mujhe doctor se milna hai
Agent: Bilkul, main appointment book kar deta hoon. Aap ka naam kya hai?

Patient: Ahmed
Agent: Ahmed bhai, aap ki age kya hai?

Patient: 40 saal
Agent: Acha. Phone number bataiye

Patient: 0300-1111111
Agent: Theek hai. Kya problem hai?

Patient: Bukhar aur dard
Agent: Samajh gaya. Kab aana hai?

Patient: kal
Agent: Kal ke liye slots check karta hoon...
```

---

## ⚠️ Urgency Detection

The system automatically detects emergency symptoms:

```
Patient: I have severe chest pain
Agent: ⚠️ URGENT: Based on your symptoms, this may be an emergency. 
Please call emergency services (115) or go to the nearest hospital immediately.
Do not wait for an appointment.
```

**Emergency keywords (English + Roman Urdu):**
- Chest pain / seene mein dard
- Difficulty breathing / sans nahi aa rahi  
- Severe bleeding / khoon beh raha
- Heart attack / dil ka daura
- Unconscious / behosh

---

## 🔔 Appointment Reminders

Automatic reminders are sent 24 hours before appointments:

```
🔔 Appointment Reminder

You have an appointment tomorrow:
Date: Saturday, January 20, 2024
Time: 02:00 PM

Please confirm or call to reschedule.
```

---

## 🛠️ Troubleshooting

### "LLM_PROVIDER not found"
- Check `.env` file exists and has `LLM_PROVIDER=gemini` (or `groq`)
- Ensure you copied `.env.example` to `.env`

### "API key not found"
- Add your API key to `.env`:
  - Gemini: Get free key from https://makersuite.google.com/app/apikey
  - Groq: Get free key from https://console.groq.com

### "Module not found" errors
- Ensure virtual environment is activated
- Re-install: `pip install -r requirements.txt`

### WhatsApp not working
- For MVP, use `WHATSAPP_MODE=stub` (console testing)
- Real mode requires Chrome browser and manual QR scan
- For production, upgrade to WhatsApp Business API

### Database errors
- Delete `clinic.db` and restart (re-creates tables)
- Check file permissions

### Port already in use
- Change port: `python app/main.py --port 8080`
- Or update `.env`: `API_PORT=8080`

---

## 📈 Next Steps (Post-MVP)

Once the MVP is working, you can add:

- ✅ **PostgreSQL**: Replace SQLite for production
- ✅ **Authentication**: Doctor login for dashboard
- ✅ **WhatsApp Business API**: Official API (paid but reliable)
- ✅ **Multiple Doctors**: Support for multiple practitioners
- ✅ **SMS Fallback**: For patients without WhatsApp
- ✅ **Payment Integration**: Online payments
- ✅ **Analytics Dashboard**: Patient trends, peak hours
- ✅ **Full Urdu Script**: Native Urdu support (not just Roman)
- ✅ **Voice Calls**: Integrate Whisper STT and gTTS
- ✅ **Appointment Rescheduling**: Patient-initiated changes

---

## 🤝 Contributing

This is an MVP. Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Fork for your own clinic

---

## 📄 License

MIT License - Use freely for commercial or personal projects.

---

## 🙏 Credits

Built with:
- **LangChain**: AI agent framework
- **FastAPI**: Modern web framework
- **Gemini/Groq**: Free LLM APIs
- **SQLAlchemy**: Database ORM
- **gTTS**: Text-to-speech
- **Whisper**: Speech-to-text (optional)

---

## 📞 Support

For questions, issues, or feature requests:
- Open an issue in the repository
- Contact the development team

---

**Made with ❤️ for clinics in Pakistan**

**Ship the MVP. Iterate quickly. Solve real problems.**
