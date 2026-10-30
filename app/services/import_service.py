import uuid
from typing import List, Dict, Any
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.stock_history import StockHistory
from app.models.user import User
from app.schemas.stock_import import StockImportRow, StockImportSuccessResponse
from app.services.permission_service import (
    require_write_permission, user_can_read_item, user_can_write_item
)

from contextlib import nullcontext
from app.services.stock_service import _sqlite_lock

def import_stock_batch(
    rows: List[StockImportRow],
    user: User,
    db: Session
):
    require_write_permission(user)

    if not rows or len(rows) > 1000:
        raise HTTPException(
            status_code=422,
            detail="Payload must contain between 1 and 1,000 rows"
        )

    lock_context = _sqlite_lock if db.bind.dialect.name == "sqlite" else nullcontext()

    with lock_context:
        # Concurrency & Deadlock Prevention (Section 2.J):
        # Sort distinct item UUIDs in ascending order so all transactions acquire locks in identical order
        distinct_item_ids = sorted(list({row.item_id for row in rows}))

    query = (
        db.query(Item)
        .filter(
            Item.id.in_(distinct_item_ids),
            Item.organization_id == user.organization_id
        )
        .order_by(Item.id.asc())
    )

    if db.bind.dialect.name != "sqlite":
        query = query.with_for_update()

    items = query.all()
    items_map: Dict[uuid.UUID, Item] = {it.id: it for it in items}

    # Sequential in-memory simulation against running balances (original request order)
    simulated_stock: Dict[uuid.UUID, int] = {it.id: it.stock for it in items}
    errors = []

    for idx, row in enumerate(rows):
        if row.quantity < 1:
            errors.append({
                "row": idx,
                "item_id": str(row.item_id),
                "reason": "Quantity must be at least 1"
            })
            continue

        if row.direction not in ("add", "remove"):
            errors.append({
                "row": idx,
                "item_id": str(row.item_id),
                "reason": "Direction must be 'add' or 'remove'"
            })
            continue

        item = items_map.get(row.item_id)
        if not item:
            errors.append({
                "row": idx,
                "item_id": str(row.item_id),
                "reason": f"Item {row.item_id} not found"
            })
            continue

        if not user_can_read_item(user, item):
            errors.append({
                "row": idx,
                "item_id": str(row.item_id),
                "reason": f"Item {row.item_id} not found"
            })
            continue

        if not user_can_write_item(user, item):
            errors.append({
                "row": idx,
                "item_id": str(row.item_id),
                "reason": f"User lacks write permission covering all locations for item {row.item_id}"
            })
            continue

        current_val = simulated_stock[row.item_id]
        if row.direction == "add":
            simulated_stock[row.item_id] = current_val + row.quantity
        elif row.direction == "remove":
            new_val = current_val - row.quantity
            if new_val < 0 and not item.allow_negative_stock:
                errors.append({
                    "row": idx,
                    "item_id": str(row.item_id),
                    "reason": f"Removal of {row.quantity} exceeds available stock ({current_val}) for item '{item.name}'"
                })
            simulated_stock[row.item_id] = new_val

    # If ANY row failed: atomic abort, return 422 with all failing rows
    if errors:
        db.rollback()
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Stock import failed",
                "errors": errors
            }
        )

    # All rows succeeded: apply stock updates and append audit history records
    initial_stock: Dict[uuid.UUID, int] = {it.id: it.stock for it in items}

    for row in rows:
        item = items_map[row.item_id]
        history = StockHistory(
            organization_id=user.organization_id,
            item_id=item.id,
            user_id=user.id,
            quantity=row.quantity,
            direction=row.direction,
            comment=row.comment,
            stock_after=simulated_stock[row.item_id]
        )
        db.add(history)

    from sqlalchemy import update
    for item_id in distinct_item_ids:
        net_delta = simulated_stock[item_id] - initial_stock[item_id]
        if net_delta != 0:
            db.execute(
                update(Item)
                .where(Item.id == item_id)
                .values(stock=Item.stock + net_delta)
            )

    db.commit()

    return StockImportSuccessResponse(
        applied=len(rows),
        message=f"Successfully applied {len(rows)} import rows"
    )
