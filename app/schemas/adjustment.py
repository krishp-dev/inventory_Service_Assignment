import uuid
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict

class StockAdjustmentCreate(BaseModel):
    quantity: int = Field(..., ge=1, description="Quantity must be at least 1")
    direction: Literal["add", "remove"] = Field(..., description="Direction must be 'add' or 'remove'")
    comment: Optional[str] = Field(None, max_length=500)

class StockHistoryResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    quantity: int
    direction: str
    comment: Optional[str]
    stock_after: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StockHistoryListResponse(BaseModel):
    items: List[StockHistoryResponse]
    total: int

