from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stock_import import StockImportRow, StockImportSuccessResponse
from app.services.auth_service import get_current_user
from app.services import import_service

router = APIRouter(prefix="/stock", tags=["Stock Import"])

@router.post("/import", response_model=StockImportSuccessResponse)
def import_stock(
    rows: List[StockImportRow],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return import_service.import_stock_batch(rows, current_user, db)

