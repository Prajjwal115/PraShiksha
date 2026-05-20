"""
backend/agent.py - Core AI Agent
Handles: LLM calls, adaptive logic, flashcard generation, session context
"""
import os
import json
import re
from typing import Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

DEFAULT_GEMINI_API_KEY = "AIzaSyBIVRoQT7kdf8NjYbrlzw6MNlEw16Pfpio"

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", DEFAULT_GEMINI_API_KEY).strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Create a .env file in the project root "
            f"and set GEMINI_API_KEY={DEFAULT_GEMINI_API_KEY}."
        )
    return genai.Client(api_key=api_key)

# ─── System Prompts ────────────────────────────────────────────────────────────

BASE_SYSTEM = """You are an intelligent, adaptive AI tutor called Prashiksha.
Your job is to teach students deeply and patiently. Always:
- Use simple, clear language appropriate to the student's level
- Provide real-world examples and analogies
- Be encouraging and supportive
- Structure responses with clear headings and bullet points
- When answering questions, always explain the underlying concepts/topics used
- Make every answer to a searched or entered query NCERT-based. Prefer NCERT curriculum framing, terminology, examples, and level-appropriate explanations.
- Adapt your depth based on how well the student understands

Understanding level context:
- 0.0–0.3: Beginner. Use very simple language, many examples, step-by-step.
- 0.4–0.6: Intermediate. Balance theory and practice.
- 0.7–1.0: Advanced. Go deeper, use technical terms, connect to advanced concepts.
"""

RESPONSE_TYPE_PROMPTS = {
    "explanation": """Provide a comprehensive explanation of the topic.
Structure: 1) Overview 2) Core concepts with elaboration 3) Real examples 4) Common misconceptions 5) Summary.
After explaining each major concept, briefly mention 2-3 sub-topics the student should know about.""",

    "qa": """The student has asked a specific question. Answer it thoroughly.
Structure: 1) Direct answer 2) Explanation of concepts used in this question 3) Elaborate on 2 key concepts 4) Related questions to explore.
Always explain the "why" behind the answer.""",

    "roadmap": """Create a structured learning roadmap for this topic.
Format your response as a JSON object wrapped in ```json ``` with this structure:
{
  "topic": "topic name",
  "overview": "brief description",
  "steps": [
    {"step": 1, "title": "step title", "content": "what to learn and why", "duration": "estimated time"},
    ...
  ],
  "total_duration": "total estimated time"
}
Include 5-8 progressive steps from beginner to advanced.""",

    "summary": """Provide a crisp, clear summary of the topic.
Structure: 1) One-line definition 2) 5 key points (bullet format) 3) 3 important terms with definitions 4) One memorable analogy.""",

    "practice": """Create a practice problem or exercise for this topic.
Structure: 1) Problem statement 2) Hints (hidden, state "Hint available if needed") 3) Expected approach (not the answer) 4) What concept this tests.
Make it progressively challenging based on understanding level."""
}

RETEACH_PROMPT = """The student answered flashcard questions on "{topic}" incorrectly.
They seem to struggle with this concept. Please reteach it using:
1. A completely different approach or analogy than before
2. A simpler, more concrete example
3. A visual or step-by-step breakdown
4. Check understanding with one simple question at the end
Be encouraging — mistakes are part of learning!"""

JOURNEY_SUMMARY_PROMPT = """The student has finished their study session. Here is their progress data:
{progress_data}

Create an encouraging journey summary with:
1. 🎯 Topics mastered today
2. 📊 Quiz performance breakdown  
3. 💪 Strengths identified
4. 📚 Areas to revisit
5. 🗺️ Recommended next steps (3-5 specific topics to explore)
6. 🌟 Motivational closing message

Keep it warm, personal, and motivating."""


# ─── AI Agent Class ────────────────────────────────────────────────────────────

class AITutorAgent:
    def __init__(self, understanding_level: float = 0.5, language: str = "en"):
        self.model_name = "gemini-2.5-flash"
        self.understanding_level = understanding_level
        self.language = language

    def _build_system_context(self, response_type: str) -> str:
        level_desc = (
            "beginner level" if self.understanding_level < 0.4
            else "intermediate level" if self.understanding_level < 0.7
            else "advanced level"
        )
        lang_note = (
            f"\n\nIMPORTANT: Respond in {self._language_name()} language. "
            f"Use natural {self._language_name()} — not a word-by-word translation."
            if self.language != "en" else ""
        )
        return (
            BASE_SYSTEM
            + f"\n\nCurrent student level: {level_desc} (score: {self.understanding_level:.1f})"
            + f"\n\nResponse style: {RESPONSE_TYPE_PROMPTS.get(response_type, RESPONSE_TYPE_PROMPTS['explanation'])}"
            + lang_note
        )

    def _language_name(self) -> str:
        names = {
            "hi": "Hindi", "mr": "Marathi", "bn": "Bengali",
            "gu": "Gujarati", "ta": "Tamil", "te": "Telugu",
            "kn": "Kannada", "pa": "Punjabi", "en": "English"
        }
        return names.get(self.language, "English")

    def _format_history(self, history: list[dict]) -> list:
        """Convert DB messages to Gemini chat format."""
        formatted = []
        for msg in history[-12:]:  # Last 12 messages for context window
            role = "user" if msg["role"] == "user" else "model"
            formatted.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
        return formatted

    def get_response(
        self,
        user_input: str,
        topic: str,
        response_type: str,
        history: list[dict]
    ) -> str:
        """Main method: get AI response with full context."""
        system_ctx = self._build_system_context(response_type)
        full_prompt = f"{system_ctx}\n\n---\n[Topic: {topic}]\n\n{user_input}"

        chat_history = self._format_history(history)

        client = get_gemini_client()
        chat = client.chats.create(
            model=self.model_name,
            history=chat_history
        )
        response = chat.send_message(full_prompt)
        return response.text

    def generate_flashcards(self, topic: str, content: str, count: int = 5) -> list[dict]:
        """Generate quiz flashcards from recent content."""
        prompt = f"""Based on this content about "{topic}":
---
{content[:2000]}
---

Generate exactly {count} flashcard questions to test understanding.
Respond ONLY with a JSON array (no markdown, no explanation):
[
  {{"question": "...", "answer": "...", "topic": "{topic}"}},
  ...
]

Questions should test real understanding, not just memorization.
Mix difficulty levels. Keep answers concise (1-3 sentences)."""

        client = get_gemini_client()
        response = client.models.generate_content(model=self.model_name, contents=prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract JSON array pattern
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return []

    def evaluate_answer(self, question: str, correct_answer: str, user_answer: str) -> dict:
        """Evaluate a student's flashcard answer."""
        prompt = f"""Evaluate this student answer:
Question: {question}
Correct answer: {correct_answer}
Student answer: {user_answer}

Respond ONLY with JSON (no markdown):
{{"is_correct": true/false, "score": 0.0-1.0, "feedback": "brief encouraging feedback", "explanation": "what was right/wrong"}}

Be generous — partial credit if they got the core idea. Score 1.0 = perfect, 0.5 = partial, 0.0 = wrong."""

        client = get_gemini_client()
        response = client.models.generate_content(model=self.model_name, contents=prompt)
        text = response.text.strip()
        text = re.sub(r"```json\s*|\s*```", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback evaluation
            user_lower = user_answer.lower()
            correct_lower = correct_answer.lower()
            key_words = set(correct_lower.split()) & set(user_lower.split())
            score = min(len(key_words) / max(len(correct_lower.split()), 1), 1.0)
            return {
                "is_correct": score > 0.6,
                "score": score,
                "feedback": "Good effort!" if score > 0.4 else "Keep trying!",
                "explanation": f"Key concepts: {correct_answer}"
            }

    def reteach_topic(self, topic: str, history: list[dict]) -> str:
        """Reteach a topic the student struggled with, using a different approach."""
        system_ctx = self._build_system_context("explanation")
        reteach = RETEACH_PROMPT.format(topic=topic)
        full_prompt = f"{system_ctx}\n\n{reteach}"

        chat_history = self._format_history(history)
        client = get_gemini_client()
        chat = client.chats.create(model=self.model_name, history=chat_history)
        response = chat.send_message(full_prompt)
        return response.text

    def generate_journey_summary(self, progress_data: dict) -> str:
        """Generate an end-of-session journey summary."""
        prompt = JOURNEY_SUMMARY_PROMPT.format(progress_data=json.dumps(progress_data, indent=2))
        client = get_gemini_client()
        response = client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    def parse_roadmap(self, response_text: str) -> Optional[dict]:
        """Extract roadmap JSON from model response."""
        match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return None

    def update_understanding(self, quiz_scores: list[float]) -> float:
        """Update understanding level based on quiz performance."""
        if not quiz_scores:
            return self.understanding_level
        avg_score = sum(quiz_scores) / len(quiz_scores)
        # Weighted update: 70% existing + 30% new quiz performance
        new_level = (self.understanding_level * 0.7) + (avg_score * 0.3)
        self.understanding_level = round(min(max(new_level, 0.0), 1.0), 2)
        return self.understanding_level
