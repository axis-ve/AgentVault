from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


UUID_TYPE = String(36)


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default")
    agent_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(42), nullable=False)
    encrypted_privkey: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    chain_id: Mapped[int] = mapped_column(Integer, nullable=False)
    last_nonce: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("label"),)

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default")
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    to_address: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_eth: Mapped[float] = mapped_column(Float, nullable=False)
    interval_seconds: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    max_base_fee_gwei: Mapped[float | None] = mapped_column(Float)
    daily_cap_eth: Mapped[float | None] = mapped_column(Float)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_tx_hash: Mapped[str | None] = mapped_column(String(120))
    spent_day: Mapped[Date | None] = mapped_column(Date)
    spent_today_eth: Mapped[float] = mapped_column(Float, default=0.0)
    config: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StrategyRun(Base):
    __tablename__ = "strategy_runs"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=_uuid_str)
    strategy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default")
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    tx_hash: Mapped[str | None] = mapped_column(String(120))
    detail: Mapped[dict | None] = mapped_column(JSON)


class MCPEvent(Base):
    __tablename__ = "mcp_events"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=_uuid_str)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="default")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_payload: Mapped[dict | None] = mapped_column(JSON)
    response_payload: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID_TYPE, primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(64), nullable=False, default="starter")
    api_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
