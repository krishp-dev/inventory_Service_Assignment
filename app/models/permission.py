import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    can_read = Column(Boolean, default=True, nullable=False)
    can_write = Column(Boolean, default=False, nullable=False)
    is_global_read = Column(Boolean, default=False, nullable=False)
    is_global_write = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="permissions")
    permission_locations = relationship("PermissionLocation", back_populates="permission", cascade="all, delete-orphan")

class PermissionLocation(Base):
    __tablename__ = "permission_locations"

    permission_id = Column(Uuid, ForeignKey("user_permissions.id", ondelete="CASCADE"), primary_key=True)
    location_id = Column(Uuid, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
    scope_type = Column(String(10), primary_key=True)  # 'READ' or 'WRITE'

    __table_args__ = (
        CheckConstraint("scope_type IN ('READ', 'WRITE')", name="chk_perm_loc_scope_type"),
    )

    permission = relationship("UserPermission", back_populates="permission_locations")
    location = relationship("Location")

