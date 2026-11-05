"""Database setup for Zuno.

SQLite by default: one file (backend/zuno.db), no server to run.
Set DATABASE_URL to switch to Postgres later, for example:
    DATABASE_URL=postgresql://user:password@localhost:5432/zuno
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# The database file lives next to this file (backend/zuno.db).
_default_db_path = Path(__file__).resolve().parents[1] / "zuno.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db_path}")

# SQLite needs this so FastAPI can use it from more than one thread.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def new_conversation_id() -> str:
    """Short random id, used for the conversation and its files folder."""
    return uuid.uuid4().hex[:12]


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=new_conversation_id)
    title = Column(String, nullable=False, default="Untitled website")
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    Base.metadata.create_all(bind=engine)
