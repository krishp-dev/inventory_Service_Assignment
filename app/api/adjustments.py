import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.adjustment import StockAdjustmentCreate, StockHistoryListResponse
from app.schemas.item import ItemResponse
from app.services.auth_service import get_current_user
from app.services import stock_service

router = APIRouter(prefix="/items", tags=["Adjustments"])

@router.post("/{id}/adjustments", response_model=ItemResponse)
def adjust_stock(
    id: uuid.UUID,
    adj_in: StockAdjustmentCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return stock_service.adjust_stock(id, adj_in, current_user, db)

@router.get("/{id}/history", response_model=StockHistoryListResponse)
def get_item_history(
    id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return stock_service.get_stock_history(id, current_user, db, limit=limit, offset=offset)

