from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any, Iterable

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import MCPEvent, Strategy, StrategyRun, Tenant, Wallet


class WalletRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def list_wallets(self) -> list[Wallet]:
        result = await self.session.execute(
            select(Wallet).where(Wallet.tenant_id == self.tenant_id)
        )
        return list(result.scalars().all())

    async def get_by_agent_id(self, agent_id: str) -> Wallet | None:
        stmt = select(Wallet).where(
            Wallet.agent_id == agent_id, Wallet.tenant_id == self.tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_wallet(
        self,
        *,
        agent_id: str,
        address: str,
        encrypted_privkey: bytes,
        chain_id: int,
        last_nonce: int | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> Wallet:
        existing = await self.get_by_agent_id(agent_id)
        if existing:
            existing.address = address
            existing.encrypted_privkey = encrypted_privkey
            existing.chain_id = chain_id
            existing.last_nonce = last_nonce
            existing.metadata_json = metadata_json or existing.metadata_json
            return existing

        record = Wallet(
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            address=address,
            encrypted_privkey=encrypted_privkey,
            chain_id=chain_id,
            last_nonce=last_nonce,
            metadata_json=metadata_json or {},
        )
        self.session.add(record)
        return record

    async def update_last_nonce(self, agent_id: str, nonce: int) -> None:
        stmt = (
            update(Wallet)
            .where(Wallet.agent_id == agent_id, Wallet.tenant_id == self.tenant_id)
            .values(last_nonce=nonce)
        )
        await self.session.execute(stmt)


class StrategyRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def list_strategies(self, agent_id: str | None = None) -> list[Strategy]:
        stmt = select(Strategy).where(Strategy.tenant_id == self.tenant_id)
        if agent_id:
            stmt = stmt.where(Strategy.agent_id == agent_id)
        result = await self.session.execute(stmt.order_by(Strategy.label))
        return list(result.scalars().all())

    async def get_by_label(self, label: str) -> Strategy | None:
        stmt = select(Strategy).where(
            Strategy.label == label, Strategy.tenant_id == self.tenant_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_strategy(
        self,
        *,
        label: str,
        agent_id: str,
        strategy_type: str,
        to_address: str,
        amount_eth: float,
        interval_seconds: int | None,
        enabled: bool,
        max_base_fee_gwei: float | None,
        daily_cap_eth: float | None,
        next_run_at: datetime | None,
        last_run_at: datetime | None,
        last_tx_hash: str | None,
        spent_day: date | None,
        spent_today_eth: float,
        config: dict | None,
    ) -> Strategy:
        record = Strategy(
            tenant_id=self.tenant_id,
            label=label,
            agent_id=agent_id,
            strategy_type=strategy_type,
            to_address=to_address,
            amount_eth=amount_eth,
            interval_seconds=interval_seconds,
            enabled=enabled,
            max_base_fee_gwei=max_base_fee_gwei,
            daily_cap_eth=daily_cap_eth,
            next_run_at=next_run_at,
            last_run_at=last_run_at,
            last_tx_hash=last_tx_hash,
            spent_day=spent_day,
            spent_today_eth=spent_today_eth,
            config=config,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def delete_strategy(self, label: str) -> Strategy | None:
        record = await self.get_by_label(label)
        if not record:
            return None
        await self.session.delete(record)
        return record


class StrategyRunRepository:
     def __init__(self, session: AsyncSession, tenant_id: str) -> None:
         self.session = session
         self.tenant_id = tenant_id
 
     async def add_run(
         self,
         *,
         strategy_id: str,
         result: str,
         tx_hash: str | None,
         detail: dict | None,
     ) -> StrategyRun:
         record = StrategyRun(
             strategy_id=strategy_id,
             tenant_id=self.tenant_id,
             run_at=datetime.now(timezone.utc),
             result=result,
             tx_hash=tx_hash,
             detail=detail,
         )
         self.session.add(record)
         return record
 
 
class EventRepository:
     def __init__(self, session: AsyncSession, tenant_id: str | None = None) -> None:
         self.session = session
         self.tenant_id = tenant_id
 
     async def record_event(
         self,
         *,
         tool_name: str,
         agent_id: str | None,
         status: str,
         request_payload: dict | None,
         response_payload: dict | None,
         error_message: str | None,
     ) -> MCPEvent:
         record = MCPEvent(
             tenant_id=self.tenant_id or "default",
             tool_name=tool_name,
             agent_id=agent_id,
             status=status,
             request_payload=request_payload,
             response_payload=response_payload,
             error_message=error_message,
             occurred_at=datetime.now(timezone.utc),
         )
         self.session.add(record)
         return record
 
     async def list_events(self, limit: int = 100) -> list[MCPEvent]:
         stmt = select(MCPEvent)
         if self.tenant_id:
             stmt = stmt.where(MCPEvent.tenant_id == self.tenant_id)
         stmt = stmt.order_by(MCPEvent.occurred_at.desc()).limit(limit)
         result = await self.session.execute(stmt)
         return list(result.scalars())
 
     async def get_event(self, event_id: str) -> MCPEvent | None:
         stmt = select(MCPEvent).where(MCPEvent.id == event_id)
         if self.tenant_id:
             stmt = stmt.where(MCPEvent.tenant_id == self.tenant_id)
         result = await self.session.execute(stmt)
         return result.scalar_one_or_none()
 
     async def count_events_since(
         self, tool_name: str, agent_id: str | None, cutoff: datetime
     ) -> int:
         stmt = select(func.count(MCPEvent.id)).where(MCPEvent.tool_name == tool_name)
         if self.tenant_id:
             stmt = stmt.where(MCPEvent.tenant_id == self.tenant_id)
         if agent_id is not None:
             stmt = stmt.where(MCPEvent.agent_id == agent_id)
         stmt = stmt.where(MCPEvent.occurred_at >= cutoff)
         result = await self.session.execute(stmt)
         return int(result.scalar_one())
 
     async def aggregate_usage(self, cutoff: datetime) -> list[dict[str, Any]]:
         stmt = select(
             MCPEvent.agent_id,
             MCPEvent.tool_name,
             func.count(MCPEvent.id).label("count"),
         ).where(MCPEvent.occurred_at >= cutoff)
         if self.tenant_id:
             stmt = stmt.where(MCPEvent.tenant_id == self.tenant_id)
         stmt = stmt.group_by(MCPEvent.agent_id, MCPEvent.tool_name).order_by(func.count(MCPEvent.id).desc())
         result = await self.session.execute(stmt)
         rows: list[dict[str, Any]] = []
         for agent_id, tool_name, count in result:
             rows.append(
                 {
                     "agent_id": agent_id,
                     "tool_name": tool_name,
                     "count": int(count),
                 }
             )
         return rows
 
 
class TenantRepository:
     def __init__(self, session: AsyncSession) -> None:
         self.session = session
 
     async def list_tenants(self) -> list[Tenant]:
         result = await self.session.execute(select(Tenant).order_by(Tenant.created_at))
         return list(result.scalars().all())
 
     async def get_by_id(self, tenant_id: str) -> Tenant | None:
         stmt = select(Tenant).where(Tenant.id == tenant_id)
         result = await self.session.execute(stmt)
         return result.scalar_one_or_none()
 
     async def get_by_name(self, name: str) -> Tenant | None:
         stmt = select(Tenant).where(Tenant.name == name)
         result = await self.session.execute(stmt)
         return result.scalar_one_or_none()
 
     async def get_by_api_key_hash(self, api_key_hash: str) -> Tenant | None:
         stmt = select(Tenant).where(Tenant.api_key_hash == api_key_hash)
         result = await self.session.execute(stmt)
         return result.scalar_one_or_none()
 
     async def create_tenant(
         self,
         *,
         name: str,
         plan: str,
         api_key_hash: str,
         metadata_json: dict | None = None,
     ) -> Tenant:
         record = Tenant(
             name=name,
             plan=plan,
             api_key_hash=api_key_hash,
             metadata_json=metadata_json or {},
         )
         self.session.add(record)
         await self.session.flush()
         return record
