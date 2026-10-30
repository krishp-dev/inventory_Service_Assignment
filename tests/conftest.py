import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.models import (
    Organization, OrganizationSettings, Location,
    User, UserPermission, PermissionLocation, Item, StockHistory
)
from app.core.security import get_password_hash, create_access_token

from sqlalchemy.pool import NullPool

TEST_DB_URL = os.getenv("TEST_DATABASE_URL", settings.TEST_DATABASE_URL)

# Test connectivity to PostgreSQL; fallback to local SQLite for local dev without postgres
if TEST_DB_URL.startswith("postgres"):
    try:
        temp_engine = create_engine(TEST_DB_URL, poolclass=NullPool)
        with temp_engine.connect() as conn:
            pass
    except Exception:
        TEST_DB_URL = "sqlite:///./inventory_test.db"

connect_args = {"check_same_thread": False} if TEST_DB_URL.startswith("sqlite") else {}

engine_test = create_engine(TEST_DB_URL, connect_args=connect_args, poolclass=NullPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine_test)
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def seed_test_data(setup_database):
    db = TestingSessionLocal()
    try:
        # Organization 1: ABC Retail
        org1 = Organization(name="ABC Retail")
        db.add(org1)
        db.flush()

        cfg1 = OrganizationSettings(organization_id=org1.id, low_stock_level=10)
        db.add(cfg1)

        loc_ahm = Location(organization_id=org1.id, name="Ahmedabad")
        loc_gan = Location(organization_id=org1.id, name="Gandhinagar")
        db.add_all([loc_ahm, loc_gan])
        db.flush()

        # Admin: read/write all locations
        u_admin = User(
            organization_id=org1.id,
            username="admin",
            password_hash=get_password_hash("Admin@12345")
        )
        db.add(u_admin)
        db.flush()
        p_admin = UserPermission(
            user_id=u_admin.id,
            organization_id=org1.id,
            can_read=True,
            can_write=True,
            is_global_read=True,
            is_global_write=True
        )
        db.add(p_admin)

        # Manager: read/write Ahmedabad only
        u_mgr = User(
            organization_id=org1.id,
            username="manager",
            password_hash=get_password_hash("Manager@12345")
        )
        db.add(u_mgr)
        db.flush()
        p_mgr = UserPermission(
            user_id=u_mgr.id,
            organization_id=org1.id,
            can_read=True,
            can_write=True,
            is_global_read=False,
            is_global_write=False
        )
        db.add(p_mgr)
        db.flush()
        pl_mgr_r = PermissionLocation(permission_id=p_mgr.id, location_id=loc_ahm.id, scope_type="READ")
        pl_mgr_w = PermissionLocation(permission_id=p_mgr.id, location_id=loc_ahm.id, scope_type="WRITE")
        db.add_all([pl_mgr_r, pl_mgr_w])

        # Viewer: read all locations, no write
        u_viewer = User(
            organization_id=org1.id,
            username="viewer",
            password_hash=get_password_hash("Viewer@12345")
        )
        db.add(u_viewer)
        db.flush()
        p_viewer = UserPermission(
            user_id=u_viewer.id,
            organization_id=org1.id,
            can_read=True,
            can_write=False,
            is_global_read=True,
            is_global_write=False
        )
        db.add(p_viewer)

        # No-Read User (for 403 test)
        u_noread = User(
            organization_id=org1.id,
            username="noread",
            password_hash=get_password_hash("NoRead@12345")
        )
        db.add(u_noread)
        db.flush()
        p_noread = UserPermission(
            user_id=u_noread.id,
            organization_id=org1.id,
            can_read=False,
            can_write=True,
            is_global_read=False,
            is_global_write=False
        )
        db.add(p_noread)

        # Organization 2: XYZ Corp (for tenant isolation tests)
        org2 = Organization(name="XYZ Corp")
        db.add(org2)
        db.flush()
        cfg2 = OrganizationSettings(organization_id=org2.id, low_stock_level=5)
        db.add(cfg2)
        loc_org2 = Location(organization_id=org2.id, name="Surat")
        db.add(loc_org2)
        db.flush()
        u_org2 = User(
            organization_id=org2.id,
            username="org2_admin",
            password_hash=get_password_hash("Org2Admin@12345")
        )
        db.add(u_org2)
        db.flush()
        p_org2 = UserPermission(
            user_id=u_org2.id,
            organization_id=org2.id,
            can_read=True,
            can_write=True,
            is_global_read=True,
            is_global_write=True
        )
        db.add(p_org2)

        db.commit()

        tokens = {
            "admin": create_access_token(u_admin.id),
            "manager": create_access_token(u_mgr.id),
            "viewer": create_access_token(u_viewer.id),
            "noread": create_access_token(u_noread.id),
            "org2": create_access_token(u_org2.id),
        }

        loc_ahm_id = loc_ahm.id
        loc_gan_id = loc_gan.id
        loc_org2_id = loc_org2.id

        return {
            "loc_ahm_id": loc_ahm_id,
            "loc_gan_id": loc_gan_id,
            "loc_org2_id": loc_org2_id,
            "tokens": tokens,
        }
    finally:
        db.close()

@pytest.fixture
def auth_headers(seed_test_data):
    return {
        k: {"Authorization": f"Bearer {token}"}
        for k, token in seed_test_data["tokens"].items()
    }
