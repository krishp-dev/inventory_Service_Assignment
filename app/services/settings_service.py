from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.settings import OrganizationSettings
from app.models.user import User
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.permission_service import (
    require_read_permission, require_global_write
)

def get_settings(user: User, db: Session) -> SettingsResponse:
    require_read_permission(user)

    cfg = db.query(OrganizationSettings).filter(OrganizationSettings.organization_id == user.organization_id).first()
    if not cfg:
        # Create default if missing
        cfg = OrganizationSettings(organization_id=user.organization_id, low_stock_level=0)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)

    return SettingsResponse(low_stock_level=cfg.low_stock_level)

def update_settings(settings_in: SettingsUpdate, user: User, db: Session) -> SettingsResponse:
    # Organization settings change only for a user whose write covers every location
    require_global_write(user)

    cfg = db.query(OrganizationSettings).filter(OrganizationSettings.organization_id == user.organization_id).first()
    if not cfg:
        cfg = OrganizationSettings(
            organization_id=user.organization_id,
            low_stock_level=settings_in.low_stock_level
        )
        db.add(cfg)
    else:
        cfg.low_stock_level = settings_in.low_stock_level

    db.commit()
    db.refresh(cfg)
    return SettingsResponse(low_stock_level=cfg.low_stock_level)

