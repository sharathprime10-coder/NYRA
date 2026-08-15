import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

# Use String(36) for UUID: compatible with both PostgreSQL and SQLite
_UUID_TYPE = String(36)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        _UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_id = Column(_UUID_TYPE, ForeignKey("users.id"))
    title = Column(String, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        _UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    session_id = Column(_UUID_TYPE, ForeignKey("chat_sessions.id"))
    role = Column(String)  # 'user' or 'ai'
    content = Column(String)
    sources = Column(String, nullable=True)  # JSON serialized string of sources
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")


class SharedKnowledgeStaging(Base):
    __tablename__ = "shared_knowledge_staging"

    id = Column(
        _UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    user_query = Column(String)
    ai_response = Column(String)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())
