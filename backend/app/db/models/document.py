import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

# Use String(36) for UUID: compatible with both PostgreSQL and SQLite
_UUID_TYPE = String(36)


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        _UUID_TYPE, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )
    filename = Column(String, index=True)
    user_id = Column(_UUID_TYPE, ForeignKey("users.id"))
    status = Column(String, default="uploaded")  # uploaded, processing, ready, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")
