from pydantic import BaseModel, Field

class SettingsResponse(BaseModel):
    low_stock_level: int

class SettingsUpdate(BaseModel):
    low_stock_level: int = Field(..., ge=0, description="low_stock_level must be 0 or greater")

