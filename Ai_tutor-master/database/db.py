"""
database/db.py - Database connection and SQLAlchemy models
"""
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    Boolean, Enum, ForeignKey, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    name          = Column(String(100), nullable=False)
    email         = Column(String(150), unique=True, nullable=False)
    language_pref = Column(String(10), default="en")
    created_at    = Column(TIMESTAMP, default=datetime.utcnow)
    last_login    = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions  = relationship("Session", back_populates="user", cascade="all, delete")
    progress  = relationship("UserProgress", back_populates="user", cascade="all, delete")


class Session(Base):
    __tablename__ = "sessions"
    id                  = Column(Integer, primary_key=True, autoincrement=True)
    user_id             = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic               = Column(String(255), nullable=False)
    response_type       = Column(Enum("explanation","qa","roadmap","summary","practice"), default="explanation")
    status              = Column(Enum("active","completed","paused"), default="active")
    understanding_level = Column(Float, default=0.5)
    started_at          = Column(TIMESTAMP, default=datetime.utcnow)
    ended_at            = Column(TIMESTAMP, nullable=True)

    user          = relationship("User", back_populates="sessions")
    messages      = relationship("Message", back_populates="session", cascade="all, delete", order_by="Message.timestamp")
    quiz_attempts = relationship("QuizAttempt", back_populates="session", cascade="all, delete")
    roadmap_steps = relationship("RoadmapStep", back_populates="session", cascade="all, delete", order_by="RoadmapStep.step_number")


class Message(Base):
    __tablename__ = "messages"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role       = Column(Enum("user","assistant","system"), nullable=False)
    content    = Column(Text, nullable=False)
    language   = Column(String(10), default="en")
    timestamp  = Column(TIMESTAMP, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    session_id     = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    topic          = Column(String(255), nullable=False)
    question       = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    user_answer    = Column(Text, nullable=True)
    is_correct     = Column(Boolean, default=False)
    score          = Column(Float, default=0.0)
    attempted_at   = Column(TIMESTAMP, default=datetime.utcnow)

    session = relationship("Session", back_populates="quiz_attempts")


class UserProgress(Base):
    __tablename__ = "user_progress"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic         = Column(String(255), nullable=False)
    mastery_score = Column(Float, default=0.0)
    sessions_count = Column(Integer, default=0)
    last_visited  = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (UniqueConstraint("user_id", "topic", name="unique_user_topic"),)
    user = relationship("User", back_populates="progress")


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    session_id   = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    step_number  = Column(Integer, nullable=False)
    step_title   = Column(String(255), nullable=False)
    step_content = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)
    completed_at = Column(TIMESTAMP, nullable=True)

    session = relationship("Session", back_populates="roadmap_steps")


# ─── Engine & Session Factory ─────────────────────────────────────────────────

def get_engine():
    db_url = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:750A%2F%2Fworkspace115@host:3306/ai_tutor_hub?charset=utf8mb4"
    )
    return create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)

def get_db_session():
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("✅ Database tables created successfully.")
