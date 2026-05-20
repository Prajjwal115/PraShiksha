"""
app.py - Prashiksha | Main Streamlit Application
Run: streamlit run app.py
"""
import streamlit as st
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from backend.agent import AITutorAgent
from backend.session_manager import SessionManager
from backend.voice import VoiceModule
from backend.translator import TranslationModule, SUPPORTED_LANGUAGES

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prashiksha",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main theme */
    .stApp { background: #0f0f1a; }
    .main .block-container { padding: 1.5rem 2rem; max-width: 1100px; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #161625; border-right: 1px solid #2a2a40; }

    /* Chat bubbles */
    .chat-user {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: white; padding: 14px 18px; border-radius: 18px 18px 4px 18px;
        margin: 8px 0 8px 15%; font-size: 15px; line-height: 1.6;
        box-shadow: 0 4px 15px rgba(99,102,241,0.3);
    }
    .chat-bot {
        background: #1e1e30; color: #e2e8f0; padding: 14px 18px;
        border-radius: 18px 18px 18px 4px; margin: 8px 15% 8px 0;
        font-size: 15px; line-height: 1.6; border: 1px solid #2a2a40;
    }
    .chat-system {
        background: #1a2e1a; color: #86efac; padding: 10px 16px;
        border-radius: 12px; margin: 6px 20%; font-size: 14px;
        border: 1px solid #16a34a40; text-align: center;
    }

    /* Cards */
    .metric-card {
        background: #1e1e30; border: 1px solid #2a2a40;
        border-radius: 12px; padding: 16px; text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: 700; color: #818cf8; }
    .metric-label { font-size: 13px; color: #94a3b8; margin-top: 4px; }

    /* Flashcard */
    .flashcard {
        background: #1e1e30; border: 2px solid #6366f1;
        border-radius: 16px; padding: 24px; margin: 12px 0;
        text-align: center; min-height: 120px;
    }
    .flashcard-question { font-size: 18px; color: #e2e8f0; font-weight: 500; }
    .flashcard-answer {
        font-size: 15px; color: #86efac; margin-top: 12px;
        padding-top: 12px; border-top: 1px solid #2a2a40;
    }

    /* Roadmap step */
    .roadmap-step {
        background: #1e1e30; border-left: 4px solid #6366f1;
        border-radius: 0 12px 12px 0; padding: 16px; margin: 8px 0;
    }
    .roadmap-step.completed { border-left-color: #22c55e; background: #1a2e1a; }
    .roadmap-step.active    { border-left-color: #f59e0b; background: #2a2214; }

    /* Response type buttons */
    .stButton > button {
        background: #1e1e30 !important; color: #c4b5fd !important;
        border: 1px solid #4c1d95 !important; border-radius: 10px !important;
        padding: 8px 16px !important; transition: all 0.2s !important;
    }
    .stButton > button:hover {
        background: #6366f1 !important; color: white !important;
        border-color: #6366f1 !important;
    }

    /* Score badge */
    .score-good  { color: #4ade80; font-weight: 700; }
    .score-ok    { color: #fbbf24; font-weight: 700; }
    .score-bad   { color: #f87171; font-weight: 700; }

    /* Section headers */
    .section-header {
        font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px;
        color: #6366f1; font-weight: 600; margin: 20px 0 10px;
    }

    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─── State Initialization ─────────────────────────────────────────────────────
def init_state():
    defaults = {
        "user": None,           # User DB object dict
        "session_id": None,
        "topic": None,
        "response_type": None,
        "chat_history": [],     # [{"role": "user"|"assistant"|"system", "content": "..."}]
        "agent": None,
        "sm": None,
        "voice": None,
        "translator": None,
        "language": "en",
        "phase": "login",       # login → setup → type_select → chat → quiz → journey
        "current_flashcards": [],
        "current_card_idx": 0,
        "quiz_answers": [],
        "roadmap_data": None,
        "current_roadmap_step": 0,
        "last_response": "",
        "understanding_level": 0.5,
        "section_content": "",  # content since last quiz
        "voice_enabled": True,
        "quiz_pending": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─── Helper: get/create SessionManager ────────────────────────────────────────
def get_sm() -> SessionManager:
    if st.session_state.sm is None:
        try:
            st.session_state.sm = SessionManager()
        except Exception as e:
            st.error(f"Database connection failed: {e}\n\nRunning in **demo mode** (no persistence).")
            st.session_state.sm = None
    return st.session_state.sm

def get_agent() -> AITutorAgent:
    if st.session_state.agent is None:
        st.session_state.agent = AITutorAgent(
            understanding_level=st.session_state.understanding_level,
            language=st.session_state.language
        )
    return st.session_state.agent

def get_voice() -> VoiceModule:
    if st.session_state.voice is None:
        st.session_state.voice = VoiceModule(language=st.session_state.language)
    return st.session_state.voice

def get_translator() -> TranslationModule:
    if st.session_state.translator is None:
        st.session_state.translator = TranslationModule()
    return st.session_state.translator


# ─── Helper: save message ─────────────────────────────────────────────────────
def save_and_display_message(role: str, content: str, display: bool = True):
    st.session_state.chat_history.append({"role": role, "content": content})
    sm = get_sm()
    if sm and st.session_state.session_id:
        try:
            sm.save_message(st.session_state.session_id, role, content, st.session_state.language)
        except Exception:
            pass  # Demo mode: just keep in memory

def add_system_msg(content: str):
    st.session_state.chat_history.append({"role": "system", "content": content})


# ─── Helper: play voice ───────────────────────────────────────────────────────
def render_top_right_noop_button():
    if not st.session_state.user:
        return
    _, right = st.columns([6, 1])
    with right:
        st.button("Button", key="top_right_noop", use_container_width=True)


def maybe_play_voice(text: str):
    if not st.session_state.voice_enabled:
        return
    voice = get_voice()
    if not voice.is_available:
        return
    try:
        audio = voice.text_to_audio_bytes(text)
        if audio:
            st.audio(audio, format=f"audio/{voice.audio_format}", autoplay=False)
    except Exception:
        pass


# ─── Sidebar ──────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎓 Prashiksha")
        st.markdown("---")

        if st.session_state.user:
            st.markdown(f"**👤 {st.session_state.user['name']}**")
            level = st.session_state.understanding_level
            level_label = "🌱 Beginner" if level < 0.4 else "📖 Intermediate" if level < 0.7 else "🚀 Expert"
            st.markdown(f"Level: {level_label}")
            st.markdown(
                f"{'**' if level < 0.4 else ''}🌱 Beginner{'**' if level < 0.4 else ''}  \n"
                f"{'**' if 0.4 <= level < 0.7 else ''}📖 Intermediate{'**' if 0.4 <= level < 0.7 else ''}  \n"
                f"{'**' if level >= 0.7 else ''}🚀 Expert{'**' if level >= 0.7 else ''}"
            )
            st.progress(level)

            st.markdown("---")

            # Language selector
            st.markdown('<div class="section-header">Language</div>', unsafe_allow_html=True)
            lang_options = list(SUPPORTED_LANGUAGES.keys())
            lang_labels  = [SUPPORTED_LANGUAGES[l] for l in lang_options]
            current_idx  = lang_options.index(st.session_state.language) if st.session_state.language in lang_options else 0
            selected_lang = st.selectbox("Respond in:", lang_labels, index=current_idx, label_visibility="collapsed")
            new_lang = lang_options[lang_labels.index(selected_lang)]
            if new_lang != st.session_state.language:
                st.session_state.language = new_lang
                agent = get_agent()
                if agent:
                    agent.language = new_lang
                voice = get_voice()
                if voice:
                    voice.set_language(new_lang)
                sm = get_sm()
                if sm and st.session_state.user:
                    try:
                        sm.update_language(st.session_state.user["id"], new_lang)
                    except Exception:
                        pass

            # Voice toggle
            st.markdown('<div class="section-header">Voice</div>', unsafe_allow_html=True)
            st.session_state.voice_enabled = st.toggle("🔊 Read responses aloud", value=st.session_state.voice_enabled)

            st.markdown("---")

            # Session info
            if st.session_state.topic:
                st.markdown('<div class="section-header">Current Session</div>', unsafe_allow_html=True)
                st.markdown(f"📚 **{st.session_state.topic}**")
                st.markdown(f"Mode: `{st.session_state.response_type or 'Not set'}`")
                messages = [m for m in st.session_state.chat_history if m["role"] in ("user","assistant")]
                st.markdown(f"Messages: **{len(messages)}**")

            st.markdown("---")

            # User progress
            sm = get_sm()
            if sm:
                try:
                    progress = sm.get_user_progress(st.session_state.user["id"])
                    if progress:
                        st.markdown('<div class="section-header">Your Topics</div>', unsafe_allow_html=True)
                        for p in sorted(progress, key=lambda x: x["mastery_score"], reverse=True)[:5]:
                            score = p["mastery_score"]
                            color = "#4ade80" if score > 0.7 else "#fbbf24" if score > 0.4 else "#f87171"
                            st.markdown(
                                f"<div style='display:flex;justify-content:space-between;margin:4px 0;font-size:13px'>"
                                f"<span>{p['topic'][:20]}</span>"
                                f"<span style='color:{color}'>{score:.0%}</span></div>",
                                unsafe_allow_html=True
                            )
                except Exception:
                    pass

            st.markdown("---")

            # Controls
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 New Topic", use_container_width=True):
                    _pause_session()
                    for key in ["session_id","topic","response_type","chat_history",
                                "current_flashcards","roadmap_data","section_content",
                                "quiz_pending","quiz_answers","current_card_idx"]:
                        st.session_state[key] = [] if key in ("chat_history","current_flashcards","quiz_answers") else None
                    st.session_state.phase = "setup"
                    st.rerun()
            with col2:
                if st.button("🏁 End Session", use_container_width=True):
                    st.session_state.phase = "journey"
                    st.rerun()


def _pause_session():
    sm = get_sm()
    if sm and st.session_state.session_id:
        try:
            sm.pause_session(st.session_state.session_id)
        except Exception:
            pass


# ─── Phase: Login ─────────────────────────────────────────────────────────────
def phase_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("# 🎓 Prashiksha")
        st.markdown("*Your adaptive AI learning companion*")
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            name  = st.text_input("Your name", placeholder="e.g. Rohan")
            email = st.text_input("Email", placeholder="rohan@example.com")
            lang  = st.selectbox("Preferred language",
                                  list(SUPPORTED_LANGUAGES.values()),
                                  index=0)
            submitted = st.form_submit_button("🚀 Start Learning", use_container_width=True)

        if submitted:
            if not name or not email:
                st.error("Please fill in your name and email.")
                return

            lang_code = [k for k,v in SUPPORTED_LANGUAGES.items() if v == lang][0]
            st.session_state.language = lang_code

            # Try DB; fallback to in-memory
            sm = get_sm()
            if sm:
                try:
                    user = sm.get_or_create_user(name, email, lang_code)
                    st.session_state.user = {
                        "id": user.id, "name": user.name,
                        "email": user.email, "language_pref": user.language_pref
                    }
                    # Check for active session to resume
                    active = sm.get_active_session(user.id)
                    if active:
                        st.session_state.session_id = active.id
                        st.session_state.topic = active.topic
                        st.session_state.response_type = active.response_type
                        history = sm.get_history(active.id)
                        st.session_state.chat_history = history
                        st.session_state.understanding_level = active.understanding_level
                        add_system_msg(f"✅ Resumed your session on **{active.topic}**! Picking up where you left off.")
                        st.session_state.phase = "chat"
                        st.rerun()
                        return
                except Exception as e:
                    st.warning(f"DB unavailable ({e}), running in demo mode.")
                    st.session_state.user = {"id": 1, "name": name, "email": email, "language_pref": lang_code}
            else:
                st.session_state.user = {"id": 1, "name": name, "email": email, "language_pref": lang_code}

            st.session_state.phase = "setup"
            st.rerun()


# ─── Phase: Setup (topic + optional resume) ───────────────────────────────────
def phase_setup():
    st.markdown(f"## 👋 Welcome back, {st.session_state.user['name']}!")
    st.markdown("**What do you want to learn today?**")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("📚 Enter a topic or question",
                               placeholder="e.g. Recursion in Python, Photosynthesis, French Revolution...",
                               label_visibility="collapsed")
    with col2:
        go = st.button("Let's Go! →", use_container_width=True, type="primary")

    if go and topic.strip():
        st.session_state.topic = topic.strip()

        # Check for previous session on same topic
        sm = get_sm()
        if sm:
            try:
                prev = sm.get_last_session_for_topic(st.session_state.user["id"], topic.strip())
                if prev:
                    st.session_state["_prev_session"] = prev.id
            except Exception:
                pass

        st.session_state.phase = "type_select"
        st.rerun()

    # Quick topic suggestions
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Quick topics:**")
    cols = st.columns(5)
    suggestions = ["Machine Learning", "Photosynthesis", "World War II", "Python Basics", "Trigonometry"]
    for i, sug in enumerate(suggestions):
        with cols[i]:
            if st.button(sug, use_container_width=True):
                st.session_state.topic = sug
                st.session_state.phase = "type_select"
                st.rerun()


# ─── Phase: Response Type Selection ──────────────────────────────────────────
def phase_type_select():
    st.markdown(f"## 📚 Topic: *{st.session_state.topic}*")

    # Resume prompt if previous session found
    prev_id = st.session_state.get("_prev_session")
    if prev_id:
        st.info(f"🔄 You've studied this topic before! Want to resume your previous session?")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Resume Previous Session"):
                sm = get_sm()
                if sm:
                    sm.resume_session(prev_id)
                    history = sm.get_history(prev_id)
                    st.session_state.session_id = prev_id
                    st.session_state.chat_history = history
                    add_system_msg(f"✅ Resumed! Continuing from where you left off on **{st.session_state.topic}**.")
                    st.session_state["_prev_session"] = None
                    st.session_state.phase = "chat"
                    st.rerun()
        with col2:
            if st.button("🆕 Start Fresh"):
                st.session_state["_prev_session"] = None
                st.rerun()
        return

    st.markdown("### How would you like to learn this?")
    st.markdown("<br>", unsafe_allow_html=True)

    TYPES = {
        "explanation": {
            "icon": "💡",
            "label": "Deep Explanation",
            "desc": "Comprehensive breakdown with examples and sub-topics"
        },
        "qa": {
            "icon": "❓",
            "label": "Q&A Mode",
            "desc": "Answer your specific question with concept elaboration"
        },
        "roadmap": {
            "icon": "🗺️",
            "label": "Roadmap Journey",
            "desc": "Step-by-step learning path from basics to advanced"
        },
        "summary": {
            "icon": "📋",
            "label": "Quick Summary",
            "desc": "Key points and definitions in a crisp format"
        },
        "practice": {
            "icon": "🏋️",
            "label": "Practice Problems",
            "desc": "Problems and exercises to apply your knowledge"
        }
    }

    cols = st.columns(3)
    type_keys = list(TYPES.keys())
    for i, (type_key, info) in enumerate(TYPES.items()):
        with cols[i % 3]:
            st.markdown(f"""
            <div style="background:#1e1e30;border:1px solid #2a2a40;border-radius:14px;padding:20px;margin:6px 0;text-align:center">
                <div style="font-size:36px">{info['icon']}</div>
                <div style="font-size:16px;font-weight:600;color:#c4b5fd;margin:8px 0">{info['label']}</div>
                <div style="font-size:13px;color:#94a3b8">{info['desc']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Choose {info['label']}", key=f"type_{type_key}", use_container_width=True):
                _start_session(type_key)
                st.rerun()


def _start_session(response_type: str):
    st.session_state.response_type = response_type
    sm = get_sm()
    if sm:
        try:
            sess = sm.create_session(
                user_id=st.session_state.user["id"],
                topic=st.session_state.topic,
                response_type=response_type
            )
            st.session_state.session_id = sess.id
        except Exception:
            st.session_state.session_id = None

    # Prime the agent with initial content
    agent = get_agent()
    welcome = f"Great! Let's explore **{st.session_state.topic}**. I'll teach you using the {response_type} approach. Ready?"
    add_system_msg(welcome)

    # Auto-generate first response
    with st.spinner("Generating your personalized content..."):
        first_prompt = f"Please begin teaching me about: {st.session_state.topic}"
        response = agent.get_response(
            user_input=first_prompt,
            topic=st.session_state.topic,
            response_type=response_type,
            history=[]
        )
        # Translate if needed
        translator = get_translator()
        if st.session_state.language != "en":
            response = translator.translate(response, st.session_state.language)

        save_and_display_message("user", first_prompt)
        save_and_display_message("assistant", response)
        st.session_state.last_response = response
        st.session_state.section_content += response

        # Handle roadmap type specially
        if response_type == "roadmap":
            roadmap = agent.parse_roadmap(response)
            if roadmap:
                st.session_state.roadmap_data = roadmap
                sm = get_sm()
                if sm and st.session_state.session_id:
                    try:
                        sm.save_roadmap_steps(st.session_state.session_id, roadmap.get("steps", []))
                    except Exception:
                        pass

    st.session_state.phase = "chat"


# ─── Phase: Chat ──────────────────────────────────────────────────────────────
def phase_chat():
    # Display chat history
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            st.markdown(f'<div class="chat-bot">{msg["content"]}</div>', unsafe_allow_html=True)
        elif msg["role"] == "system":
            st.markdown(f'<div class="chat-system">💬 {msg["content"]}</div>', unsafe_allow_html=True)

    # Voice play for last assistant message
    last_assistant = next(
        (m["content"] for m in reversed(st.session_state.chat_history) if m["role"] == "assistant"),
        None
    )
    if last_assistant:
        maybe_play_voice(last_assistant)

    st.markdown("<br>", unsafe_allow_html=True)

    # Roadmap progress bar
    if st.session_state.roadmap_data:
        render_roadmap_sidebar()

    # Quiz trigger button (show after enough content)
    content_len = len(st.session_state.section_content)
    if content_len > 300 and not st.session_state.quiz_pending:
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("🃏 Test Yourself!", use_container_width=True):
                st.session_state.quiz_pending = True
                st.session_state.phase = "quiz"
                st.rerun()
        with col3:
            if st.button("🏁 End Session", use_container_width=True):
                st.session_state.phase = "journey"
                st.rerun()

    # Chat input
    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "Your message",
                placeholder="Ask a follow-up, say 'explain more', 'give an example', 'next topic'...",
                label_visibility="collapsed"
            )
        with col2:
            send = st.form_submit_button("Send →", use_container_width=True)

    if send and user_input.strip():
        _handle_chat(user_input.strip())
        st.rerun()


def _handle_chat(user_input: str):
    save_and_display_message("user", user_input)

    agent = get_agent()
    sm    = get_sm()

    # Check for special commands
    lower = user_input.lower()
    if any(k in lower for k in ["end session", "finish", "goodbye", "bye", "done learning"]):
        st.session_state.phase = "journey"
        return
    if any(k in lower for k in ["quiz", "test me", "flashcard", "test myself"]):
        st.session_state.quiz_pending = True
        st.session_state.phase = "quiz"
        return

    with st.spinner("Thinking..."):
        history = st.session_state.chat_history[:-1]  # exclude the message we just added
        response = agent.get_response(
            user_input=user_input,
            topic=st.session_state.topic,
            response_type=st.session_state.response_type,
            history=history
        )
        translator = get_translator()
        if st.session_state.language != "en":
            response = translator.translate(response, st.session_state.language)

        save_and_display_message("assistant", response)
        st.session_state.last_response = response
        st.session_state.section_content += "\n" + response

        # Every ~3 assistant messages, suggest a quiz
        assistant_msgs = sum(1 for m in st.session_state.chat_history if m["role"] == "assistant")
        if assistant_msgs > 0 and assistant_msgs % 3 == 0:
            add_system_msg("💡 You've covered a good chunk! Want to test yourself with some flashcards?")


def render_roadmap_sidebar():
    roadmap = st.session_state.roadmap_data
    if not roadmap:
        return
    steps = roadmap.get("steps", [])
    total = len(steps)
    done  = st.session_state.current_roadmap_step
    st.markdown(f"**🗺️ Roadmap: {roadmap.get('topic','')}** — Step {done+1}/{total}")
    st.progress(done / total if total else 0)
    if done < total and st.button(f"✅ Complete: {steps[done].get('title','')}", use_container_width=True):
        st.session_state.current_roadmap_step += 1
        sm = get_sm()
        if sm and st.session_state.session_id:
            try:
                sm.complete_roadmap_step(st.session_state.session_id, done + 1)
            except Exception:
                pass
        add_system_msg(f"✅ Completed step {done+1}: **{steps[done].get('title','')}**! Moving on...")
        st.rerun()
    st.markdown("---")


# ─── Phase: Quiz / Flashcards ─────────────────────────────────────────────────
def phase_quiz():
    st.markdown("## 🃏 Flashcard Quiz")
    st.markdown(f"*Testing your understanding of: **{st.session_state.topic}***")
    st.markdown("<br>", unsafe_allow_html=True)

    # Generate flashcards if not already done
    if not st.session_state.current_flashcards:
        with st.spinner("Generating flashcards..."):
            agent = get_agent()
            cards = agent.generate_flashcards(
                topic=st.session_state.topic,
                content=st.session_state.section_content
            )
            if not cards:
                st.error("Couldn't generate flashcards. Let's continue chatting!")
                st.session_state.phase = "chat"
                st.rerun()
                return
            st.session_state.current_flashcards = cards
            st.session_state.current_card_idx = 0
            st.session_state.quiz_answers = []

    cards = st.session_state.current_flashcards
    idx   = st.session_state.current_card_idx

    # All cards done
    if idx >= len(cards):
        _show_quiz_results()
        return

    # Current card
    card = cards[idx]
    st.markdown(f"**Question {idx+1} of {len(cards)}**")
    st.progress((idx) / len(cards))

    st.markdown(f"""
    <div class="flashcard">
        <div class="flashcard-question">{card['question']}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form(f"quiz_form_{idx}", clear_on_submit=True):
        answer = st.text_area("Your answer:", placeholder="Type your answer here...", height=100, label_visibility="collapsed")
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("✅ Submit Answer", use_container_width=True)
        with col2:
            skip = st.form_submit_button("⏭️ Skip", use_container_width=True)

    if submit and answer.strip():
        with st.spinner("Evaluating..."):
            agent = get_agent()
            eval_result = agent.evaluate_answer(
                question=card["question"],
                correct_answer=card["answer"],
                user_answer=answer.strip()
            )

        is_correct = eval_result.get("is_correct", False)
        score      = eval_result.get("score", 0.0)
        feedback   = eval_result.get("feedback", "")
        explanation = eval_result.get("explanation", card["answer"])

        # Show result
        if is_correct:
            st.success(f"✅ {feedback}")
        elif score > 0.4:
            st.warning(f"🌟 Partially correct! {feedback}")
        else:
            st.error(f"❌ {feedback}")

        st.markdown(f"""
        <div class="flashcard">
            <div class="flashcard-question">{card['question']}</div>
            <div class="flashcard-answer">✅ Answer: {explanation}</div>
        </div>
        """, unsafe_allow_html=True)

        # Save attempt
        sm = get_sm()
        if sm and st.session_state.session_id:
            try:
                sm.save_quiz_attempt(
                    session_id=st.session_state.session_id,
                    topic=card.get("topic", st.session_state.topic),
                    question=card["question"],
                    correct_answer=card["answer"],
                    user_answer=answer.strip(),
                    is_correct=is_correct,
                    score=score
                )
            except Exception:
                pass

        st.session_state.quiz_answers.append({"card": card, "score": score, "is_correct": is_correct})

        time.sleep(0.5)
        st.session_state.current_card_idx += 1
        st.rerun()

    if skip:
        st.session_state.quiz_answers.append({"card": card, "score": 0.0, "is_correct": False})
        st.session_state.current_card_idx += 1
        st.rerun()


def _show_quiz_results():
    answers = st.session_state.quiz_answers
    if not answers:
        st.session_state.phase = "chat"
        st.rerun()
        return

    total   = len(answers)
    correct = sum(1 for a in answers if a["is_correct"])
    avg     = sum(a["score"] for a in answers) / total
    pct     = int(avg * 100)

    # Update understanding level
    agent = get_agent()
    scores = [a["score"] for a in answers]
    new_level = agent.update_understanding(scores)
    st.session_state.understanding_level = new_level
    sm = get_sm()
    if sm and st.session_state.session_id:
        try:
            sm.update_understanding(
                st.session_state.session_id, new_level,
                st.session_state.user["id"], st.session_state.topic
            )
        except Exception:
            pass

    # Results display
    st.markdown("## 📊 Quiz Results")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{correct}/{total}</div><div class="metric-label">Correct</div></div>', unsafe_allow_html=True)
    with col2:
        color = "score-good" if pct >= 70 else "score-ok" if pct >= 40 else "score-bad"
        st.markdown(f'<div class="metric-card"><div class="metric-value {color}">{pct}%</div><div class="metric-label">Score</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{new_level:.0%}</div><div class="metric-label">Understanding</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Identify weak topics
    weak = [a["card"].get("topic", st.session_state.topic) for a in answers if not a["is_correct"]]
    weak = list(set(weak))

    if pct >= 70:
        st.success("🎉 Excellent! You've got a strong understanding. Let's continue!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Continue Learning", use_container_width=True):
                st.session_state.current_flashcards = []
                st.session_state.quiz_answers = []
                st.session_state.section_content = ""
                st.session_state.quiz_pending = False
                st.session_state.phase = "chat"
                add_system_msg(f"🎯 Quiz done — {pct}% score! Great job! Let's keep going.")
                st.rerun()
        with col2:
            if st.button("🏁 End Session", use_container_width=True):
                st.session_state.phase = "journey"
                st.rerun()
    else:
        st.warning(f"📖 Some areas need more work ({100-pct}% of questions were tricky).")
        if weak:
            st.markdown(f"**Weak areas:** {', '.join(weak)}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Reteach Weak Topics", use_container_width=True):
                st.session_state.current_flashcards = []
                st.session_state.quiz_answers = []
                st.session_state.section_content = ""
                st.session_state.quiz_pending = False
                st.session_state.phase = "chat"
                # Trigger reteach
                with st.spinner("Preparing a new explanation..."):
                    for topic in weak[:2]:  # reteach top 2 weak topics
                        reteach_response = agent.reteach_topic(topic, st.session_state.chat_history)
                        translator = get_translator()
                        if st.session_state.language != "en":
                            reteach_response = translator.translate(reteach_response, st.session_state.language)
                        save_and_display_message("assistant", reteach_response)
                        st.session_state.section_content += reteach_response
                add_system_msg(f"🔄 Let's revisit the tricky parts with a fresh approach!")
                st.rerun()
        with col2:
            if st.button("▶️ Continue Anyway", use_container_width=True):
                st.session_state.current_flashcards = []
                st.session_state.quiz_answers = []
                st.session_state.section_content = ""
                st.session_state.quiz_pending = False
                st.session_state.phase = "chat"
                add_system_msg(f"Moving on! Feel free to ask if anything is still unclear.")
                st.rerun()
        with col3:
            if st.button("🏁 End Session", use_container_width=True):
                st.session_state.phase = "journey"
                st.rerun()


# ─── Phase: Journey Summary ───────────────────────────────────────────────────
def phase_journey():
    sm  = get_sm()
    if sm and st.session_state.session_id:
        try:
            sm.end_session(st.session_state.session_id)
        except Exception:
            pass

    st.markdown("## 🏁 Your Learning Journey")
    st.markdown(f"*Session on: **{st.session_state.topic}***")
    st.markdown("<br>", unsafe_allow_html=True)

    # Build progress data
    if sm and st.session_state.session_id:
        try:
            journey_data = sm.get_session_journey_data(
                session_id=st.session_state.session_id,
                user_id=st.session_state.user["id"],
                topic=st.session_state.topic or "General"
            )
        except Exception:
            journey_data = _build_local_journey_data()
    else:
        journey_data = _build_local_journey_data()

    # Summary metrics
    qr = journey_data.get("quiz_results", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        mins = journey_data.get("session_duration_minutes", 0)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{mins}</div><div class="metric-label">Minutes</div></div>', unsafe_allow_html=True)
    with col2:
        msgs = journey_data.get("messages_exchanged", len(st.session_state.chat_history))
        st.markdown(f'<div class="metric-card"><div class="metric-value">{msgs}</div><div class="metric-label">Messages</div></div>', unsafe_allow_html=True)
    with col3:
        acc = qr.get("accuracy_percent", 0)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{acc:.0f}%</div><div class="metric-label">Quiz Accuracy</div></div>', unsafe_allow_html=True)
    with col4:
        level = journey_data.get("understanding_level", st.session_state.understanding_level)
        st.markdown(f'<div class="metric-card"><div class="metric-value">{level:.0%}</div><div class="metric-label">Mastery</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # AI-generated journey summary
    with st.spinner("Generating your personalized journey summary..."):
        agent = get_agent()
        summary = agent.generate_journey_summary(journey_data)
        translator = get_translator()
        if st.session_state.language != "en":
            summary = translator.translate(summary, st.session_state.language)

    st.markdown(f'<div class="chat-bot">{summary}</div>', unsafe_allow_html=True)
    maybe_play_voice(summary)

    st.markdown("<br>", unsafe_allow_html=True)

    # Roadmap completion
    if st.session_state.roadmap_data:
        steps = st.session_state.roadmap_data.get("steps", [])
        done  = st.session_state.current_roadmap_step
        st.markdown("### 🗺️ Roadmap Progress")
        for i, step in enumerate(steps):
            status = "completed" if i < done else "active" if i == done else ""
            icon   = "✅" if i < done else "🔵" if i == done else "⚪"
            st.markdown(f"""
            <div class="roadmap-step {status}">
                {icon} <strong>Step {i+1}: {step.get('title','')}</strong>
                <div style="font-size:13px;color:#94a3b8;margin-top:4px">{step.get('content','')[:100]}...</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📚 Study Another Topic", use_container_width=True, type="primary"):
            for key in ["session_id","topic","response_type","chat_history","current_flashcards",
                        "roadmap_data","section_content","quiz_pending","quiz_answers",
                        "current_card_idx","current_roadmap_step","last_response"]:
                st.session_state[key] = (
                    [] if key in ("chat_history","current_flashcards","quiz_answers") else
                    0  if key in ("current_card_idx","current_roadmap_step") else
                    None
                )
            st.session_state.section_content = ""
            st.session_state.phase = "setup"
            st.rerun()
    with col2:
        if st.button("🔚 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_state()
            st.rerun()


def _build_local_journey_data() -> dict:
    history = st.session_state.chat_history
    return {
        "topic": st.session_state.topic or "General",
        "session_duration_minutes": 0,
        "messages_exchanged": sum(1 for m in history if m["role"] in ("user","assistant")),
        "quiz_results": {
            "total_questions": len(st.session_state.quiz_answers),
            "correct_answers": sum(1 for a in st.session_state.quiz_answers if a.get("is_correct")),
            "average_score": sum(a.get("score",0) for a in st.session_state.quiz_answers) / max(len(st.session_state.quiz_answers),1),
            "accuracy_percent": round(
                sum(a.get("score",0) for a in st.session_state.quiz_answers) / max(len(st.session_state.quiz_answers),1) * 100, 1
            )
        },
        "understanding_level": st.session_state.understanding_level,
        "weak_topics": [],
        "roadmap_progress": {"total_steps": 0, "completed_steps": 0, "completed_titles": []},
        "overall_progress": []
    }


# ─── Main Router ──────────────────────────────────────────────────────────────
render_sidebar()

phase = st.session_state.phase

if phase != "login":
    render_top_right_noop_button()

if phase == "login":
    phase_login()
elif phase == "setup":
    phase_setup()
elif phase == "type_select":
    phase_type_select()
elif phase == "chat":
    phase_chat()
elif phase == "quiz":
    phase_quiz()
elif phase == "journey":
    phase_journey()
