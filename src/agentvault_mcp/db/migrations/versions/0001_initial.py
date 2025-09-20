"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("address", sa.String(length=42), nullable=False),
        sa.Column("encrypted_privkey", sa.LargeBinary(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("last_nonce", sa.Integer()),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "strategies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("label", sa.String(length=255), nullable=False, unique=True),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column("to_address", sa.String(length=64), nullable=False),
        sa.Column("amount_eth", sa.Float(), nullable=False),
        sa.Column("interval_seconds", sa.Integer()),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("0")),
        sa.Column("max_base_fee_gwei", sa.Float()),
        sa.Column("daily_cap_eth", sa.Float()),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_tx_hash", sa.String(length=120)),
        sa.Column("spent_day", sa.Date()),
        sa.Column("spent_today_eth", sa.Float(), server_default=sa.text("0")),
        sa.Column("config", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )

    op.create_table(
        "strategy_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("strategy_id", sa.String(length=36), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("tx_hash", sa.String(length=120)),
        sa.Column("detail", sa.JSON()),
    )

    op.create_table(
        "mcp_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("tool_name", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=255)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_payload", sa.JSON()),
        sa.Column("response_payload", sa.JSON()),
        sa.Column("error_message", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("mcp_events")
    op.drop_table("strategy_runs")
    op.drop_table("strategies")
    op.drop_table("wallets")
