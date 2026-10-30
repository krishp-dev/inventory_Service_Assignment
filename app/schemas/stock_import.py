import uuid
from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class StockImportRow(BaseModel):
    item_id: uuid.UUID
    quantity: int = Field(..., ge=1)
    direction: Literal["add", "remove"]
    comment: Optional[str] = Field(None, max_length=500)

class StockImportRowError(BaseModel):
    row: int
    item_id: Optional[uuid.UUID]
    reason: str

class StockImportErrorResponse(BaseModel):
    detail: str
    errors: List[StockImportRowError]

class StockImportSuccessResponse(BaseModel):
    applied: int
    message: str

