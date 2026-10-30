import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    low_stock_level = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("low_stock_level >= 0", name="chk_org_low_stock_level_non_negative"),
    )

    organization = relationship("Organization", back_populates="settings")

