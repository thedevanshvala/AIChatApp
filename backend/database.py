from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import re

# ─────────────────────────────────────
# Base
# ─────────────────────────────────────

Base = declarative_base()

# ─────────────────────────────────────
# Models
# ─────────────────────────────────────

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer)

    # "user" or "assistant"
    role = Column(String)

    content = Column(Text)

    # store uploaded file extracted text
    file_content = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

# ─────────────────────────────────────
# Dynamic Database Per User
# ─────────────────────────────────────

def get_database(username: str):

    # sanitize username
    safe_username = re.sub(
        r'[^a-zA-Z0-9_]',
        '',
        username
    )

    # fallback
    if not safe_username:
        safe_username = "default"

    DATABASE_URL = f"sqlite:///./{safe_username}.db"

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False
        }
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    # create tables automatically
    Base.metadata.create_all(bind=engine)

    # return database session
    return SessionLocal()