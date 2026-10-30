import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Table, Uuid, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

item_locations = Table(
    "item_locations",
    Base.metadata,
    Column("item_id", Uuid, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Uuid, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True)
)

class Item(Base):
    __tablename__ = "items"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    stock = Column(Integer, default=0, nullable=False)
    allow_negative_stock = Column(Boolean, default=False, nullable=False)
    attributes = Column(JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_org_item_name"),
    )

    organization = relationship("Organization", back_populates="items")
    locations = relationship("Location", secondary=item_locations, back_populates="items", lazy="joined")
    history_entries = relationship("StockHistory", back_populates="item", cascade="all, delete-orphan", order_by="desc(StockHistory.created_at)")

