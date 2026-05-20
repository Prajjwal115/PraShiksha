"""
backend/session_manager.py - Session lifecycle management
Handles: creating/resuming sessions, saving messages, tracking progress
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session as DBSession

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db import (
    User, Session, Message, QuizAttempt, UserProgress, RoadmapStep, get_db_session
)


class SessionManager:
    def __init__(self):
        self.db: DBSession = get_db_session()

    # ─── User ─────────────────────────────────────────────────────────────────

    def get_or_create_user(self, name: str, email: str, language: str = "en") -> User:
        user = self.db.query(User).filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, language_pref=language)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            user.last_login = datetime.utcnow()
            if language != "en":
                user.language_pref = language
            self.db.commit()
        return user

    def update_language(self, user_id: int, language: str):
        user = self.db.query(User).get(user_id)
        if user:
            user.language_pref = language
            self.db.commit()

    # ─── Session ──────────────────────────────────────────────────────────────

    def create_session(self, user_id: int, topic: str, response_type: str) -> Session:
        session = Session(
            user_id=user_id,
            topic=topic,
            response_type=response_type,
            status="active"
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        self._increment_topic_sessions(user_id, topic)
        return session

    def get_active_session(self, user_id: int) -> Optional[Session]:
        return (
            self.db.query(Session)
            .filter_by(user_id=user_id, status="active")
            .order_by(Session.started_at.desc())
            .first()
        )

    def get_last_session_for_topic(self, user_id: int, topic: str) -> Optional[Session]:
        return (
            self.db.query(Session)
            .filter_by(user_id=user_id, topic=topic)
            .filter(Session.status.in_(["paused", "completed"]))
            .order_by(Session.started_at.desc())
            .first()
        )

    def resume_session(self, session_id: int) -> Optional[Session]:
        session = self.db.query(Session).get(session_id)
        if session:
            session.status = "active"
            self.db.commit()
        return session

    def pause_session(self, session_id: int):
        session = self.db.query(Session).get(session_id)
        if session:
            session.status = "paused"
            self.db.commit()

    def end_session(self, session_id: int):
        session = self.db.query(Session).get(session_id)
        if session:
            session.status = "completed"
            session.ended_at = datetime.utcnow()
            self.db.commit()

    def update_understanding(self, session_id: int, level: float, user_id: int = None, topic: str = None):
        session = self.db.query(Session).get(session_id)
        if session:
            session.understanding_level = level
            self.db.commit()
        if user_id and topic:
            self._update_mastery(user_id, topic, level)

    # ─── Messages ─────────────────────────────────────────────────────────────

    def save_message(self, session_id: int, role: str, content: str, language: str = "en") -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            language=language
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_history(self, session_id: int, limit: int = 20) -> list[dict]:
        messages = (
            self.db.query(Message)
            .filter_by(session_id=session_id)
            .filter(Message.role.in_(["user", "assistant"]))
            .order_by(Message.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {"role": m.role, "content": m.content, "timestamp": str(m.timestamp)}
            for m in reversed(messages)
        ]

    # ─── Quiz / Flashcards ────────────────────────────────────────────────────

    def save_quiz_attempt(
        self, session_id: int, topic: str, question: str,
        correct_answer: str, user_answer: str, is_correct: bool, score: float
    ) -> QuizAttempt:
        attempt = QuizAttempt(
            session_id=session_id, topic=topic, question=question,
            correct_answer=correct_answer, user_answer=user_answer,
            is_correct=is_correct, score=score
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_quiz_scores(self, session_id: int) -> list[float]:
        attempts = self.db.query(QuizAttempt).filter_by(session_id=session_id).all()
        return [a.score for a in attempts]

    def get_weak_topics(self, session_id: int, threshold: float = 0.5) -> list[str]:
        attempts = self.db.query(QuizAttempt).filter_by(session_id=session_id).all()
        topic_scores: dict[str, list] = {}
        for a in attempts:
            topic_scores.setdefault(a.topic, []).append(a.score)
        return [
            t for t, scores in topic_scores.items()
            if sum(scores) / len(scores) < threshold
        ]

    # ─── Progress ─────────────────────────────────────────────────────────────

    def _increment_topic_sessions(self, user_id: int, topic: str):
        prog = self.db.query(UserProgress).filter_by(user_id=user_id, topic=topic).first()
        if prog:
            prog.sessions_count += 1
        else:
            prog = UserProgress(user_id=user_id, topic=topic, sessions_count=1)
            self.db.add(prog)
        self.db.commit()

    def _update_mastery(self, user_id: int, topic: str, score: float):
        prog = self.db.query(UserProgress).filter_by(user_id=user_id, topic=topic).first()
        if prog:
            prog.mastery_score = round((prog.mastery_score * 0.6) + (score * 0.4), 2)
            prog.last_visited = datetime.utcnow()
        else:
            prog = UserProgress(user_id=user_id, topic=topic, mastery_score=score)
            self.db.add(prog)
        self.db.commit()

    def get_user_progress(self, user_id: int) -> list[dict]:
        entries = self.db.query(UserProgress).filter_by(user_id=user_id).all()
        return [
            {
                "topic": e.topic,
                "mastery_score": e.mastery_score,
                "sessions_count": e.sessions_count,
                "last_visited": str(e.last_visited)
            }
            for e in entries
        ]

    # ─── Roadmap ──────────────────────────────────────────────────────────────

    def save_roadmap_steps(self, session_id: int, steps: list[dict]):
        for s in steps:
            step = RoadmapStep(
                session_id=session_id,
                step_number=s.get("step", 0),
                step_title=s.get("title", ""),
                step_content=s.get("content", "")
            )
            self.db.add(step)
        self.db.commit()

    def complete_roadmap_step(self, session_id: int, step_number: int):
        step = (
            self.db.query(RoadmapStep)
            .filter_by(session_id=session_id, step_number=step_number)
            .first()
        )
        if step:
            step.is_completed = True
            step.completed_at = datetime.utcnow()
            self.db.commit()

    def get_roadmap_steps(self, session_id: int) -> list[dict]:
        steps = self.db.query(RoadmapStep).filter_by(session_id=session_id).order_by(RoadmapStep.step_number).all()
        return [
            {
                "step": s.step_number,
                "title": s.step_title,
                "content": s.step_content,
                "is_completed": s.is_completed
            }
            for s in steps
        ]

    # ─── Journey Data ─────────────────────────────────────────────────────────

    def get_session_journey_data(self, session_id: int, user_id: int, topic: str) -> dict:
        session = self.db.query(Session).get(session_id)
        history = self.get_history(session_id)
        attempts = self.db.query(QuizAttempt).filter_by(session_id=session_id).all()
        progress = self.get_user_progress(user_id)

        total_questions = len(attempts)
        correct_count = sum(1 for a in attempts if a.is_correct)
        avg_score = sum(a.score for a in attempts) / total_questions if total_questions else 0

        weak_topics = self.get_weak_topics(session_id)
        steps = self.get_roadmap_steps(session_id)
        completed_steps = [s for s in steps if s["is_completed"]]

        return {
            "topic": topic,
            "session_duration_minutes": (
                (datetime.utcnow() - session.started_at).seconds // 60
                if session else 0
            ),
            "messages_exchanged": len(history),
            "quiz_results": {
                "total_questions": total_questions,
                "correct_answers": correct_count,
                "average_score": round(avg_score, 2),
                "accuracy_percent": round((correct_count / total_questions * 100) if total_questions else 0, 1)
            },
            "understanding_level": session.understanding_level if session else 0.5,
            "weak_topics": weak_topics,
            "roadmap_progress": {
                "total_steps": len(steps),
                "completed_steps": len(completed_steps),
                "completed_titles": [s["title"] for s in completed_steps]
            },
            "overall_progress": progress
        }

    def close(self):
        self.db.close()
