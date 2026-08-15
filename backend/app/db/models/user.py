import uuid

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.database import Base

# Use String(36) for UUID to stay compatible with both PostgreSQL and SQLite.
# In production on PostgreSQL, UUIDs are stored as text in the UUID column.
_UUID_TYPE = String(36)


class User(Base):
    __tablename__ = "users"

    id = Column(_UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    xp = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_active = Column(DateTime(timezone=True), nullable=True)
