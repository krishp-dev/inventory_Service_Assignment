import uuid
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.services.auth_service import get_current_user
from app.services import item_service

router = APIRouter(prefix="/items", tags=["Items"])

@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(
    item_in: ItemCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return item_service.create_item(item_in, current_user, db)

@router.get("", response_model=ItemListResponse)
def list_items(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return item_service.list_items(current_user, db, limit=limit, offset=offset)

@router.get("/{id}", response_model=ItemResponse)
def get_item(
    id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return item_service.get_item_by_id(id, current_user, db)

@router.put("/{id}", response_model=ItemResponse)
def update_item(
    id: uuid.UUID,
    item_in: ItemUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return item_service.update_item(id, item_in, current_user, db)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    id: uuid.UUID,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    item_service.delete_item(id, current_user, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

