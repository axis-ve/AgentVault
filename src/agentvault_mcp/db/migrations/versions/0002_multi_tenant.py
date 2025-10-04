"""multi-tenant schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_multi_tenant"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("plan", sa.String(length=64), nullable=False, server_default="starter"),
        sa.Column("api_key_hash", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    with op.batch_alter_table("wallets") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default="default"))
        batch.create_index("ix_wallets_tenant_id", ["tenant_id"], unique=False)

    with op.batch_alter_table("strategies") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default="default"))
        batch.create_index("ix_strategies_tenant_id", ["tenant_id"], unique=False)

    with op.batch_alter_table("strategy_runs") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default="default"))
        batch.create_index("ix_strategy_runs_tenant_id", ["tenant_id"], unique=False)

    with op.batch_alter_table("mcp_events") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=36), nullable=False, server_default="default"))
        batch.create_index("ix_mcp_events_tenant_id", ["tenant_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("mcp_events") as batch:
        batch.drop_index("ix_mcp_events_tenant_id")
        batch.drop_column("tenant_id")

    with op.batch_alter_table("strategy_runs") as batch:
        batch.drop_index("ix_strategy_runs_tenant_id")
        batch.drop_column("tenant_id")

    with op.batch_alter_table("strategies") as batch:
        batch.drop_index("ix_strategies_tenant_id")
        batch.drop_column("tenant_id")

    with op.batch_alter_table("wallets") as batch:
        batch.drop_index("ix_wallets_tenant_id")
        batch.drop_column("tenant_id")

    op.drop_table("tenants")

