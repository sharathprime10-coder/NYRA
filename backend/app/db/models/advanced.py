import uuid

from sqlalchemy import JSON as JSONB  # Use JSON for cross-DB compatibility
from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.sql import func

from app.db.database import Base

# Use String for UUID columns when PostgreSQL UUID type isn't available
_UUID_TYPE = String(36)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(_UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(_UUID_TYPE, ForeignKey("users.id"))
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(_UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(_UUID_TYPE, ForeignKey("users.id"))
    session_id = Column(_UUID_TYPE, ForeignKey("chat_sessions.id"))
    trace_id = Column(String, index=True)
    agent_name = Column(String)
    status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(_UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    agent_run_id = Column(_UUID_TYPE, ForeignKey("agent_runs.id"))
    tool_name = Column(String)
    arguments = Column(JSONB)
    execution_time = Column(Float)
    status = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(_UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(_UUID_TYPE, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    resource_type = Column(String)
    resource_id = Column(String)
    metadata_info = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
