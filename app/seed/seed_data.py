import sys
import os
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import SessionLocal, engine
from app.models import (
    Base, Organization, OrganizationSettings, Location,
    User, UserPermission, PermissionLocation, Item, StockHistory
)
from app.core.security import get_password_hash, create_access_token

def run_seed(db: Session) -> dict:
    print("🌱 Running idempotent seed for ABC Retail...")

    # 1. Organization
    org = db.query(Organization).filter_by(name="ABC Retail").first()
    if not org:
        org = Organization(name="ABC Retail")
        db.add(org)
        db.flush()
        print(f"  Created Organization: {org.name} ({org.id})")
    else:
        print(f"  Found Organization: {org.name} ({org.id})")

    # 2. Organization Settings (low_stock_level = 10)
    cfg = db.query(OrganizationSettings).filter_by(organization_id=org.id).first()
    if not cfg:
        cfg = OrganizationSettings(organization_id=org.id, low_stock_level=10)
        db.add(cfg)
        db.flush()

    # 3. Locations: Ahmedabad and Gandhinagar
    loc_ahm = db.query(Location).filter_by(organization_id=org.id, name="Ahmedabad").first()
    if not loc_ahm:
        loc_ahm = Location(organization_id=org.id, name="Ahmedabad")
        db.add(loc_ahm)
        db.flush()

    loc_gan = db.query(Location).filter_by(organization_id=org.id, name="Gandhinagar").first()
    if not loc_gan:
        loc_gan = Location(organization_id=org.id, name="Gandhinagar")
        db.add(loc_gan)
        db.flush()

    print(f"  Locations: Ahmedabad ({loc_ahm.id}), Gandhinagar ({loc_gan.id})")

    # 4. Users & Permissions
    # - admin: read/write all locations
    user_admin = db.query(User).filter_by(organization_id=org.id, username="admin").first()
    if not user_admin:
        user_admin = User(
            organization_id=org.id,
            username="admin",
            password_hash=get_password_hash("Admin@12345")
        )
        db.add(user_admin)
        db.flush()

        perm_admin = UserPermission(
            user_id=user_admin.id,
            organization_id=org.id,
            can_read=True,
            can_write=True,
            is_global_read=True,
            is_global_write=True
        )
        db.add(perm_admin)
        db.flush()

    # - manager: read/write Ahmedabad only
    user_mgr = db.query(User).filter_by(organization_id=org.id, username="manager").first()
    if not user_mgr:
        user_mgr = User(
            organization_id=org.id,
            username="manager",
            password_hash=get_password_hash("Manager@12345")
        )
        db.add(user_mgr)
        db.flush()

        perm_mgr = UserPermission(
            user_id=user_mgr.id,
            organization_id=org.id,
            can_read=True,
            can_write=True,
            is_global_read=False,
            is_global_write=False
        )
        db.add(perm_mgr)
        db.flush()

        pl_mgr_read = PermissionLocation(
            permission_id=perm_mgr.id,
            location_id=loc_ahm.id,
            scope_type="READ"
        )
        pl_mgr_write = PermissionLocation(
            permission_id=perm_mgr.id,
            location_id=loc_ahm.id,
            scope_type="WRITE"
        )
        db.add_all([pl_mgr_read, pl_mgr_write])
        db.flush()

    # - viewer: read all locations, no write permission
    user_viewer = db.query(User).filter_by(organization_id=org.id, username="viewer").first()
    if not user_viewer:
        user_viewer = User(
            organization_id=org.id,
            username="viewer",
            password_hash=get_password_hash("Viewer@12345")
        )
        db.add(user_viewer)
        db.flush()

        perm_viewer = UserPermission(
            user_id=user_viewer.id,
            organization_id=org.id,
            can_read=True,
            can_write=False,
            is_global_read=True,
            is_global_write=False
        )
        db.add(perm_viewer)
        db.flush()

    # 5. Items:
    # - Laptop: stock 50, all locations
    item_laptop = db.query(Item).filter_by(organization_id=org.id, name="Laptop").first()
    if not item_laptop:
        item_laptop = Item(
            organization_id=org.id,
            name="Laptop",
            stock=50,
            allow_negative_stock=False,
            attributes={"color": "silver", "size": "15-inch", "weight_grams": 1800, "brand": "TechCorp"},
            locations=[]  # Empty means all locations
        )
        db.add(item_laptop)
        db.flush()
        hist = StockHistory(
            organization_id=org.id,
            item_id=item_laptop.id,
            user_id=user_admin.id,
            quantity=50,
            direction="add",
            comment="Initial stocking",
            stock_after=50
        )
        db.add(hist)

    # - Keyboard: stock 100, Ahmedabad
    item_kb = db.query(Item).filter_by(organization_id=org.id, name="Keyboard").first()
    if not item_kb:
        item_kb = Item(
            organization_id=org.id,
            name="Keyboard",
            stock=100,
            allow_negative_stock=False,
            attributes={"color": "black", "size": "TKL", "weight_grams": 750, "switch": "Cherry Red"},
            locations=[loc_ahm]
        )
        db.add(item_kb)
        db.flush()
        hist = StockHistory(
            organization_id=org.id,
            item_id=item_kb.id,
            user_id=user_admin.id,
            quantity=100,
            direction="add",
            comment="Initial stocking",
            stock_after=100
        )
        db.add(hist)

    # - Mouse: stock 80, Gandhinagar
    item_mouse = db.query(Item).filter_by(organization_id=org.id, name="Mouse").first()
    if not item_mouse:
        item_mouse = Item(
            organization_id=org.id,
            name="Mouse",
            stock=80,
            allow_negative_stock=False,
            attributes={"color": "white", "size": "Standard", "weight_grams": 95, "dpi": 16000},
            locations=[loc_gan]
        )
        db.add(item_mouse)
        db.flush()
        hist = StockHistory(
            organization_id=org.id,
            item_id=item_mouse.id,
            user_id=user_admin.id,
            quantity=80,
            direction="add",
            comment="Initial stocking",
            stock_after=80
        )
        db.add(hist)

    db.commit()

    tokens = {
        "admin": create_access_token(user_admin.id),
        "manager": create_access_token(user_mgr.id),
        "viewer": create_access_token(user_viewer.id),
    }

    print("\n" + "="*70)
    print("✅ SEED COMPLETED SUCCESSFULLY")
    print("="*70)
    print("DEMO CREDENTIALS & JWT TOKENS:")
    print(f"1. Admin (Full access across all locations):")
    print(f"   Username: admin | Password: Admin@12345")
    print(f"   JWT: {tokens['admin']}\n")
    print(f"2. Manager (Read/Write Ahmedabad only):")
    print(f"   Username: manager | Password: Manager@12345")
    print(f"   JWT: {tokens['manager']}\n")
    print(f"3. Viewer (Read all locations, no write):")
    print(f"   Username: viewer | Password: Viewer@12345")
    print(f"   JWT: {tokens['viewer']}")
    print("="*70)

    return {
        "org_id": org.id,
        "locations": {"Ahmedabad": loc_ahm.id, "Gandhinagar": loc_gan.id},
        "items": {"Laptop": item_laptop.id, "Keyboard": item_kb.id, "Mouse": item_mouse.id},
        "users": {"admin": user_admin.id, "manager": user_mgr.id, "viewer": user_viewer.id},
        "tokens": tokens
    }

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()

