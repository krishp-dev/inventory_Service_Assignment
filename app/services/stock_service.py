import uuid
import threading
from contextlib import nullcontext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.stock_history import StockHistory
from app.models.user import User
from app.schemas.adjustment import StockAdjustmentCreate, StockHistoryResponse, StockHistoryListResponse
from app.schemas.item import ItemResponse
from app.services.permission_service import get_accessible_item
from app.services.item_service import format_item_response, get_org_low_stock_level

_sqlite_lock = threading.Lock()

def adjust_stock(
    item_id: uuid.UUID,
    adj_in: StockAdjustmentCreate,
    user: User,
    db: Session
) -> ItemResponse:
    # On PostgreSQL: SELECT ... FOR UPDATE provides row-level mutual exclusion
    # On SQLite (which lacks row locks): fallback thread lock emulates row locking for multi-threaded tests
    lock_context = _sqlite_lock if db.bind.dialect.name == "sqlite" else nullcontext()

    with lock_context:
        # Pessimistic row-level lock (SELECT ... FOR UPDATE) inside atomic transaction
        item = get_accessible_item(db, item_id, user, for_write=True, lock=True)

        if adj_in.direction == "add":
            new_stock = item.stock + adj_in.quantity
        elif adj_in.direction == "remove":
            new_stock = item.stock - adj_in.quantity
            if new_stock < 0 and not item.allow_negative_stock:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Adjustment would result in negative stock ({new_stock}) for item '{item.name}'"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Direction must be 'add' or 'remove'"
            )

        item.stock = new_stock

        history = StockHistory(
            organization_id=user.organization_id,
            item_id=item.id,
            user_id=user.id,
            quantity=adj_in.quantity,
            direction=adj_in.direction,
            comment=adj_in.comment,
            stock_after=new_stock
        )
        db.add(history)
        db.commit()
        db.refresh(item)

        low_stock_level = get_org_low_stock_level(db, user.organization_id)
        return format_item_response(item, low_stock_level)

def get_stock_history(
    item_id: uuid.UUID,
    user: User,
    db: Session,
    limit: int = 20,
    offset: int = 0
) -> StockHistoryListResponse:
    # Verifies user read permission and location visibility (raises 404 if inaccessible)
    item = get_accessible_item(db, item_id, user, for_write=False)

    query = db.query(StockHistory).filter(StockHistory.item_id == item.id)
    total = query.count()
    entries = (
        query.order_by(StockHistory.created_at.desc(), StockHistory.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return StockHistoryListResponse(
        items=[
            StockHistoryResponse(
                id=e.id,
                item_id=e.item_id,
                user_id=e.user_id,
                quantity=e.quantity,
                direction=e.direction,
                comment=e.comment,
                stock_after=e.stock_after,
                created_at=e.created_at
            )
            for e in entries
        ],
        total=total
    )
