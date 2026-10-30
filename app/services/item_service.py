import uuid
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.models.item import Item
from app.models.location import Location
from app.models.settings import OrganizationSettings
from app.models.user import User
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from app.services.permission_service import (
    require_write_permission, require_read_permission,
    get_accessible_item, filter_items_for_user,
    get_user_write_location_ids
)

def get_org_low_stock_level(db: Session, org_id: uuid.UUID) -> int:
    cfg = db.query(OrganizationSettings).filter(OrganizationSettings.organization_id == org_id).first()
    return cfg.low_stock_level if cfg else 0

def format_item_response(item: Item, low_stock_level: int) -> ItemResponse:
    loc_ids = [loc.id for loc in item.locations]
    return ItemResponse(
        id=item.id,
        name=item.name,
        location_ids=loc_ids,
        stock=item.stock,
        allow_negative_stock=item.allow_negative_stock,
        attributes=item.attributes or {},
        low_stock=(item.stock <= low_stock_level),
        created_at=item.created_at,
        updated_at=item.updated_at
    )

def validate_location_ids(location_ids: List[uuid.UUID], org_id: uuid.UUID, db: Session) -> List[Location]:
    if not location_ids:
        return []
    locations = db.query(Location).filter(
        Location.id.in_(location_ids),
        Location.organization_id == org_id
    ).all()
    if len(locations) != len(set(location_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more location_ids are invalid or belong to another organization"
        )
    return locations

def merge_managed_attributes(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Section 3.5 & Master Prompt:
    - attributes is PostgreSQL JSONB.
    - The API manages: color, size, weight_grams.
    - Unknown keys must survive updates.
    - A PUT containing unchanged GET data must not change stored database state.
    - Never overwrite unrelated JSON keys.
    """
    merged = dict(existing or {})
    for key in settings.MANAGED_ATTRIBUTES:
        if key in incoming:
            merged[key] = incoming[key]
    return merged

def create_item(item_in: ItemCreate, user: User, db: Session) -> ItemResponse:
    require_write_permission(user)

    # Validate locations belong to user's organization
    locations = validate_location_ids(item_in.location_ids, user.organization_id, db)

    # If user does not have global write, they cannot create an item available everywhere
    if not item_in.location_ids and not user.permissions.is_global_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global write permission required to create an item available at all locations"
        )

    # If item specifies locations, user must have write access covering all those locations
    if item_in.location_ids and not user.permissions.is_global_write:
        user_write_ids = get_user_write_location_ids(user)
        if not set(item_in.location_ids).issubset(user_write_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User lacks write permission covering all locations specified for this item"
            )

    item = Item(
        organization_id=user.organization_id,
        name=item_in.name,
        stock=0,  # Stock is strictly read-only on item creation
        allow_negative_stock=item_in.allow_negative_stock,
        attributes=item_in.attributes or {},
        locations=locations
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    low_stock_level = get_org_low_stock_level(db, user.organization_id)
    return format_item_response(item, low_stock_level)

def list_items(user: User, db: Session, limit: int = 20, offset: int = 0) -> ItemListResponse:
    require_read_permission(user)

    query = db.query(Item)
    query = filter_items_for_user(query, user)

    total = query.count()
    items = query.order_by(Item.created_at.asc(), Item.id.asc()).offset(offset).limit(limit).all()

    low_stock_level = get_org_low_stock_level(db, user.organization_id)
    return ItemListResponse(
        items=[format_item_response(it, low_stock_level) for it in items],
        total=total
    )

def get_item_by_id(item_id: uuid.UUID, user: User, db: Session) -> ItemResponse:
    item = get_accessible_item(db, item_id, user, for_write=False)
    low_stock_level = get_org_low_stock_level(db, user.organization_id)
    return format_item_response(item, low_stock_level)

def update_item(item_id: uuid.UUID, item_in: ItemUpdate, user: User, db: Session) -> ItemResponse:
    item = get_accessible_item(db, item_id, user, for_write=True)

    if item_in.name is not None:
        item.name = item_in.name

    if item_in.allow_negative_stock is not None:
        item.allow_negative_stock = item_in.allow_negative_stock

    if item_in.location_ids is not None:
        # Validate locations belong to org
        locations = validate_location_ids(item_in.location_ids, user.organization_id, db)
        
        # Verify user has write coverage for updated locations
        if not item_in.location_ids and not user.permissions.is_global_write:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Global write permission required to make an item available everywhere"
            )
        if item_in.location_ids and not user.permissions.is_global_write:
            user_write_ids = get_user_write_location_ids(user)
            if not set(item_in.location_ids).issubset(user_write_ids):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User lacks write permission for updated locations"
                )
        item.locations = locations

    if item_in.attributes is not None:
        item.attributes = merge_managed_attributes(item.attributes, item_in.attributes)

    # Note: item.stock is never updated from ItemUpdate (strictly read-only on PUT /items/{id})
    db.commit()
    db.refresh(item)

    low_stock_level = get_org_low_stock_level(db, user.organization_id)
    return format_item_response(item, low_stock_level)

def delete_item(item_id: uuid.UUID, user: User, db: Session) -> None:
    item = get_accessible_item(db, item_id, user, for_write=True)
    db.delete(item)
    db.commit()

