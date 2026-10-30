import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, CheckConstraint, Uuid
from sqlalchemy.orm import relationship
from app.db.base import Base

def utcnow():
    return datetime.now(timezone.utc)

class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(Uuid, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    quantity = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=False)  # 'add' or 'remove'
    comment = Column(String(500), nullable=True)
    stock_after = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="chk_stock_history_quantity_gte_1"),
        CheckConstraint("direction IN ('add', 'remove')", name="chk_stock_history_direction_valid"),
    )

    organization = relationship("Organization")
    item = relationship("Item", back_populates="history_entries")
    user = relationship("User")

