"""
Memory module – stores user profiles, conversation history, and emotion patterns.

Uses SQLite via SQLAlchemy so the service works locally with no extra setup.
"""

import datetime
import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jarvis_memory.db")
_connect_args: dict = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    preferences = Column(Text, default="{}")  # JSON string
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ConversationEntry(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    emotion = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class EmotionRecord(Base):
    __tablename__ = "emotion_patterns"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    emotion = Column(String, nullable=False)
    context = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


# Create tables on import
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_memory(
    user_id: str,
    role: str,
    content: str,
    emotion: Optional[str] = None,
) -> None:
    """Persist a single conversation turn to the database."""
    db: Session = SessionLocal()
    try:
        entry = ConversationEntry(
            user_id=user_id,
            role=role,
            content=content,
            emotion=emotion,
        )
        db.add(entry)

        # Also record emotion pattern
        if emotion:
            db.add(EmotionRecord(user_id=user_id, emotion=emotion, context=content[:200]))

        # Upsert user profile
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            db.add(UserProfile(user_id=user_id))

        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("save_memory failed: %s", exc)
        raise
    finally:
        db.close()


def get_memory(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve the most recent *limit* conversation turns for a user."""
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(ConversationEntry)
            .filter_by(user_id=user_id)
            .order_by(ConversationEntry.timestamp.desc())
            .limit(limit)
            .all()
        )
        rows = list(reversed(rows))  # oldest first
        return [
            {
                "role": r.role,
                "content": r.content,
                "emotion": r.emotion,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ]
    finally:
        db.close()


def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Fetch user profile; creates a default one if it doesn't exist yet."""
    db: Session = SessionLocal()
    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return {
            "user_id": profile.user_id,
            "name": profile.name,
            "preferences": json.loads(profile.preferences or "{}"),
        }
    finally:
        db.close()


def update_user_profile(user_id: str, name: Optional[str] = None, preferences: Optional[Dict] = None) -> None:
    """Update user profile fields."""
    db: Session = SessionLocal()
    try:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        if name is not None:
            profile.name = name
        if preferences is not None:
            existing = json.loads(profile.preferences or "{}")
            existing.update(preferences)
            profile.preferences = json.dumps(existing)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("update_user_profile failed: %s", exc)
        raise
    finally:
        db.close()


def get_emotion_patterns(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Return recent emotion records for a user."""
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(EmotionRecord)
            .filter_by(user_id=user_id)
            .order_by(EmotionRecord.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [{"emotion": r.emotion, "timestamp": r.timestamp.isoformat()} for r in rows]
    finally:
        db.close()
