import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location_ids: List[uuid.UUID] = Field(default_factory=list)
    allow_negative_stock: bool = False
    attributes: Dict[str, Any] = Field(default_factory=dict)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location_ids: Optional[List[uuid.UUID]] = None
    allow_negative_stock: Optional[bool] = None
    attributes: Optional[Dict[str, Any]] = None

class ItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    location_ids: List[uuid.UUID]
    stock: int
    allow_negative_stock: bool
    attributes: Dict[str, Any]
    low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    total: int

