"""initial normalized schema with UUIDs

Revision ID: 0001_initial
Revises: 
Create Date: 2026-10-30 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. organization_settings
    op.create_table(
        'organization_settings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('low_stock_level', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('low_stock_level >= 0', name='chk_org_low_stock_level_non_negative'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )
    op.create_index('ix_org_settings_org_id', 'organization_settings', ['organization_id'])

    # 3. locations
    op.create_table(
        'locations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_location_name')
    )
    op.create_index('ix_locations_org_id', 'locations', ['organization_id'])

    # 4. users
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'username', name='uq_org_username')
    )
    op.create_index('ix_users_org_id', 'users', ['organization_id'])

    # 5. user_permissions
    op.create_table(
        'user_permissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('can_read', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('can_write', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_global_read', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_global_write', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index('ix_user_permissions_user_id', 'user_permissions', ['user_id'])

    # 6. permission_locations
    op.create_table(
        'permission_locations',
        sa.Column('permission_id', sa.Uuid(), nullable=False),
        sa.Column('location_id', sa.Uuid(), nullable=False),
        sa.Column('scope_type', sa.String(length=10), nullable=False),
        sa.CheckConstraint("scope_type IN ('READ', 'WRITE')", name='chk_perm_loc_scope_type'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['permission_id'], ['user_permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('permission_id', 'location_id', 'scope_type')
    )

    # 7. items
    op.create_table(
        'items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('stock', sa.Integer(), server_default='0', nullable=False),
        sa.Column('allow_negative_stock', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), 'sqlite'), server_default=sa.text("'{}'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_org_item_name')
    )
    op.create_index('ix_items_org_id', 'items', ['organization_id'])

    # 8. item_locations
    op.create_table(
        'item_locations',
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('location_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('item_id', 'location_id')
    )

    # 9. stock_history
    op.create_table(
        'stock_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=False),
        sa.Column('comment', sa.String(length=500), nullable=True),
        sa.Column('stock_after', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint('quantity >= 1', name='chk_stock_history_quantity_gte_1'),
        sa.CheckConstraint("direction IN ('add', 'remove')", name='chk_stock_history_direction_valid'),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stock_history_item_id', 'stock_history', ['item_id'])
    op.create_index('ix_stock_history_created_at', 'stock_history', ['created_at'])


def downgrade() -> None:
    op.drop_table('stock_history')
    op.drop_table('item_locations')
    op.drop_table('items')
    op.drop_table('permission_locations')
    op.drop_table('user_permissions')
    op.drop_table('users')
    op.drop_table('locations')
    op.drop_table('organization_settings')
    op.drop_table('organizations')

