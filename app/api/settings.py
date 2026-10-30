from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.auth_service import get_current_user
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=SettingsResponse)
def get_settings(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return settings_service.get_settings(current_user, db)

@router.put("", response_model=SettingsResponse)
def update_settings(
    settings_in: SettingsUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return settings_service.update_settings(settings_in, current_user, db)

