# 🎓 Prashiksha

An adaptive AI learning companion that teaches any topic using personalized content,
multilingual support, flashcard quizzes, voice narration, and persistent MySQL storage.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **Adaptive AI** | Adjusts depth & style based on quiz performance |
| 📚 **5 Learning Modes** | Explanation, Q&A, Roadmap, Summary, Practice |
| 🃏 **Flashcard Quizzes** | Auto-generated after each section, with smart evaluation |
| 🔄 **Re-teach Engine** | Uses a new method if student struggles |
| 🌐 **11 Languages** | Hindi, Marathi, Bengali, Gujarati, Tamil, Telugu, Kannada, Punjabi, Malayalam, Urdu, English |
| 🔊 **Voice Narration** | gTTS reads all responses aloud (multilingual) |
| 💾 **Session Persistence** | MySQL stores chat history; resume from where you left off |
| 🗺️ **Learning Roadmap** | Step-by-step topic journey with progress tracking |
| 📊 **Journey Summary** | AI-generated session recap with next steps |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <your-repo>
cd ai_tutor

pip install -r requirements.txt
```

### 2. Set up MySQL

```bash
# Start MySQL and run the schema
mysql -u root -p < database/schema.sql
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and fill in:
#   GEMINI_API_KEY=AIzaSyBIVRoQT7kdf8NjYbrlzw6MNlEw16Pfpio
#   DATABASE_URL=mysql+pymysql://root:750A%2F%2Fworkspace115@host:3306/ai_tutor_hub?charset=utf8mb4
```

Get a **free Gemini API key** at: https://aistudio.google.com/app/apikey

### 4. Run the App

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## 📁 Project Structure

```
ai_tutor/
├── app.py                    # Main Streamlit app (UI + routing)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
│
├── backend/
│   ├── agent.py              # AI Agent (Gemini, adaptive logic, quiz generation)
│   ├── session_manager.py    # DB operations (sessions, messages, progress)
│   ├── voice.py              # Text-to-Speech (gTTS / pyttsx3)
│   └── translator.py         # Language translation (deep-translator)
│
└── database/
    ├── schema.sql             # MySQL schema (run once)
    └── db.py                  # SQLAlchemy models & connection
```

---

## 🔄 How the Learning Flow Works

```
Student enters topic
        ↓
Choose response type (Explanation / Q&A / Roadmap / Summary / Practice)
        ↓
AI generates personalized content (in chosen language)
        ↓
Adaptive chat continues (student asks follow-ups, AI adjusts depth)
        ↓
After ~300 chars of content → Flashcard quiz trigger
        ↓
Quiz evaluation (Gemini evaluates answers with partial credit)
        ↓
If score ≥ 70%  → Continue to next section
If score < 70%  → Student chooses: Re-teach (new method) or Continue
        ↓
Understanding level updated → AI adapts future responses
        ↓
Session ends → AI generates journey summary + next steps
        ↓
Chat stored in MySQL → Can resume next time
```

---

## 🛠️ Demo Mode (No Database)

If MySQL is not available, the app runs in **demo mode**:
- Chat history stored in Streamlit session state only
- No persistence between browser refreshes
- All other features (AI, quiz, voice, translation) work normally

---

## 🌐 Language Support

The AI natively responds in the student's language using:
1. **Gemini's multilingual capability** (primary — best quality for major Indian languages)
2. **deep-translator** (fallback for translation after English response)

Supported: English, Hindi, Marathi, Bengali, Gujarati, Tamil, Telugu, Kannada, Punjabi, Urdu, Malayalam

---

## 🔊 Voice Setup

**Online (recommended):** `gTTS` — supports all 11 languages. Requires internet.

```bash
pip install gTTS
```

**Offline fallback:** `pyttsx3` — English only, no internet needed.

```bash
pip install pyttsx3
```

---

## 🧩 Extending the Project

### Add a new response type
1. Add to `RESPONSE_TYPE_PROMPTS` in `backend/agent.py`
2. Add the UI card in `phase_type_select()` in `app.py`
3. Add to the MySQL ENUM in `database/schema.sql`

### Switch to OpenAI GPT-4o
In `backend/agent.py`, replace the Gemini calls:
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
response = client.chat.completions.create(model="gpt-4o", messages=[...])
```

### Add external APIs (Wikipedia, YouTube, Khan Academy)
Use the `get_response()` method in `agent.py` — inject API results into the prompt before sending to the LLM.

---

## 📊 Database Schema

| Table | Purpose |
|---|---|
| `users` | Student profile, language preference |
| `sessions` | One per study session, tracks understanding level |
| `messages` | Full chat history per session |
| `quiz_attempts` | Every flashcard answer with score |
| `user_progress` | Cross-session mastery score per topic |
| `roadmap_steps` | Individual steps in roadmap sessions |

---

## 🏆 Hackathon Tips

- **Start demo**: Run without MySQL first (demo mode works out of the box)
- **Free tier**: Gemini 1.5 Flash has generous free limits — perfect for hackathons
- **Judges love**: Show the adaptive re-teach flow — it's the most impressive feature
- **Deploy**: Use Streamlit Cloud (free) + PlanetScale (free MySQL) for a live demo

---

Built with ❤️ using Python, Streamlit, Google Gemini, MySQL, gTTS, and deep-translator.
