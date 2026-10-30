import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    locations = relationship("Location", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="organization", cascade="all, delete-orphan")
    settings = relationship("OrganizationSettings", back_populates="organization", uselist=False, cascade="all, delete-orphan")

