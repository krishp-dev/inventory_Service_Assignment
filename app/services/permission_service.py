import uuid
from typing import Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.models.item import Item
from app.models.location import Location

def require_read_permission(user: User) -> None:
    if not user.permissions or not user.permissions.can_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Read permission required"
        )

def require_write_permission(user: User) -> None:
    if not user.permissions or not user.permissions.can_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission required"
        )

def require_global_write(user: User) -> None:
    if not user.permissions or not user.permissions.can_write or not user.permissions.is_global_write:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write permission covering every location is required to change organization settings"
        )

def get_user_read_location_ids(user: User) -> Set[uuid.UUID]:
    if not user.permissions:
        return set()
    return {
        pl.location_id
        for pl in user.permissions.permission_locations
        if pl.scope_type == "READ"
    }

def get_user_write_location_ids(user: User) -> Set[uuid.UUID]:
    if not user.permissions:
        return set()
    return {
        pl.location_id
        for pl in user.permissions.permission_locations
        if pl.scope_type == "WRITE"
    }

def user_can_read_item(user: User, item: Item) -> bool:
    """
    Section 3.1 & 3.2:
    - User only sees items belonging to their organization.
    - If user has global read access, user sees all items in org.
    - If user read covers only some locations:
      An item is readable when its effective locations intersect the user's read scope.
      An item with empty locations is available at all organization locations,
      so it intersects any location the user can read.
    """
    if item.organization_id != user.organization_id:
        return False

    if not user.permissions or not user.permissions.can_read:
        return False

    if user.permissions.is_global_read:
        return True

    item_location_ids = {loc.id for loc in item.locations}
    user_read_ids = get_user_read_location_ids(user)

    if not item_location_ids:
        # Available across all organization locations
        return len(user_read_ids) > 0

    return bool(item_location_ids.intersection(user_read_ids))

def user_can_write_item(user: User, item: Item) -> bool:
    """
    Section 3.2 & Master Prompt:
    - For writes, require permission covering every affected location.
    - For an item available everywhere (empty locations), only global write access can modify it.
    - For an item at listed locations, user's write locations must cover ALL item locations.
    """
    if item.organization_id != user.organization_id:
        return False

    if not user.permissions or not user.permissions.can_write:
        return False

    if user.permissions.is_global_write:
        return True

    item_location_ids = {loc.id for loc in item.locations}
    if not item_location_ids:
        # Item is available everywhere; requires global write access
        return False

    user_write_ids = get_user_write_location_ids(user)
    # User must have write permission covering EVERY location where the item is available
    return item_location_ids.issubset(user_write_ids)

def get_accessible_item(
    db: Session,
    item_id: uuid.UUID,
    user: User,
    for_write: bool = False,
    lock: bool = False
) -> Item:
    """
    Centralized Item Lookup enforcing:
    - 404 for non-existent or other organization's item
    - 404 for item outside user's readable locations
    - 403 if write requested without necessary location coverage
    """
    require_read_permission(user)

    query = db.query(Item).filter(
        Item.id == item_id,
        Item.organization_id == user.organization_id
    )

    if lock and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()

    item = query.first()

    if not item or not user_can_read_item(user, item):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )

    if for_write:
        require_write_permission(user)
        if not user_can_write_item(user, item):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User lacks write permission covering all locations for this item"
            )

    return item

def filter_items_for_user(query, user: User):
    """
    Applies organization and location filtering to Item queries.
    """
    query = query.filter(Item.organization_id == user.organization_id)
    if not user.permissions or not user.permissions.can_read:
        return query.filter(Item.id == None)  # Return empty query if no read permission

    if not user.permissions.is_global_read:
        user_read_ids = get_user_read_location_ids(user)
        if user_read_ids:
            query = query.filter(
                or_(
                    ~Item.locations.any(),
                    Item.locations.any(Location.id.in_(user_read_ids))
                )
            )
        else:
            query = query.filter(Item.id == None)
    return query

