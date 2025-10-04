"""Stateful strategy manager backed by the VaultPilot database."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from . import WalletError
from .wallet import AgentWalletManager
from .db.repositories import StrategyRepository, StrategyRunRepository
from .db.models import Strategy


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> Optional[str]:
    return dt.isoformat() if dt else None


def _from_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass
class DcaStrategy:
    label: str
    agent_id: str
    to_address: str
    amount_eth: float
    interval_seconds: int
    enabled: bool = False
    max_base_fee_gwei: Optional[float] = None
    daily_cap_eth: Optional[float] = None
    next_run_at: Optional[str] = None
    last_run_at: Optional[str] = None
    last_tx_hash: Optional[str] = None
    spent_day: Optional[str] = None
    spent_today_eth: float = 0.0

    def due(self, now: Optional[datetime] = None) -> bool:
        if not self.enabled:
            return False
        if not self.next_run_at:
            return True
        now = now or _utcnow()
        try:
            nxt = datetime.fromisoformat(self.next_run_at)
        except ValueError:
            return True
        comparison_now = now
        if nxt.tzinfo is None and comparison_now.tzinfo is not None:
            comparison_now = comparison_now.replace(tzinfo=None)
        elif nxt.tzinfo is not None and comparison_now.tzinfo is None:
            comparison_now = comparison_now.replace(tzinfo=nxt.tzinfo)
        return comparison_now >= nxt

    def schedule_next(self, now: Optional[datetime] = None) -> None:
        now = now or _utcnow()
        nxt = now + timedelta(seconds=self.interval_seconds)
        self.next_run_at = nxt.isoformat()

    def reset_daily_if_needed(self, now: Optional[datetime] = None) -> None:
        now = now or _utcnow()
        day = now.date().isoformat()
        if self.spent_day != day:
            self.spent_day = day
            self.spent_today_eth = 0.0


class StrategyManager:
    def __init__(self, wallet: AgentWalletManager):
        self.wallet = wallet
        self.session_maker = wallet.session_maker
        self._locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, label: str) -> asyncio.Lock:
        if label not in self._locks:
            self._locks[label] = asyncio.Lock()
        return self._locks[label]

    def _record_to_strategy(self, record: Strategy) -> DcaStrategy:
        return DcaStrategy(
            label=record.label,
            agent_id=record.agent_id,
            to_address=record.to_address,
            amount_eth=record.amount_eth,
            interval_seconds=record.interval_seconds or 0,
            enabled=record.enabled,
            max_base_fee_gwei=record.max_base_fee_gwei,
            daily_cap_eth=record.daily_cap_eth,
            next_run_at=_iso(record.next_run_at),
            last_run_at=_iso(record.last_run_at),
            last_tx_hash=record.last_tx_hash,
            spent_day=record.spent_day.isoformat() if record.spent_day else None,
            spent_today_eth=record.spent_today_eth or 0.0,
        )

    def _apply_strategy_to_record(self, strategy: DcaStrategy, record: Strategy) -> None:
        record.enabled = strategy.enabled
        record.next_run_at = _from_iso(strategy.next_run_at)
        record.last_run_at = _from_iso(strategy.last_run_at)
        record.last_tx_hash = strategy.last_tx_hash
        record.spent_today_eth = strategy.spent_today_eth
        record.spent_day = (
            datetime.fromisoformat(strategy.spent_day).date() if strategy.spent_day else None
        )

    async def list_strategies(self) -> Dict[str, Dict[str, Any]]:
        async with self.session_maker() as session:
            repo = StrategyRepository(session, self.wallet.tenant_id)
            records = await repo.list_strategies()
        return {record.label: asdict(self._record_to_strategy(record)) for record in records}

    async def list_strategies_for_agent(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        async with self.session_maker() as session:
            repo = StrategyRepository(session, self.wallet.tenant_id)
            records = await repo.list_strategies(agent_id=agent_id)
        return {record.label: asdict(self._record_to_strategy(record)) for record in records}

    async def create_strategy_dca(
        self,
        label: str,
        agent_id: str,
        to_address: str,
        amount_eth: float,
        interval_seconds: int,
        *,
        max_base_fee_gwei: Optional[float] = None,
        daily_cap_eth: Optional[float] = None,
    ) -> Dict[str, Any]:
        async with self.session_maker() as session:
            async with session.begin():
                repo = StrategyRepository(session, self.wallet.tenant_id)
                existing = await repo.get_by_label(label)
                if existing:
                    raise WalletError(f"Strategy '{label}' already exists")
                record = await repo.create_strategy(
                    label=label,
                    agent_id=agent_id,
                    strategy_type="dca",
                    to_address=to_address,
                    amount_eth=amount_eth,
                    interval_seconds=interval_seconds,
                    enabled=False,
                    max_base_fee_gwei=max_base_fee_gwei,
                    daily_cap_eth=daily_cap_eth,
                    next_run_at=None,
                    last_run_at=None,
                    last_tx_hash=None,
                    spent_day=None,
                    spent_today_eth=0.0,
                    config={},
                )
        return asdict(self._record_to_strategy(record))

    async def start_strategy(self, label: str) -> Dict[str, Any]:
        async with self.session_maker() as session:
            async with session.begin():
                repo = StrategyRepository(session, self.wallet.tenant_id)
                record = await repo.get_by_label(label)
                if not record:
                    raise WalletError(f"Strategy '{label}' not found")
                strategy = self._record_to_strategy(record)
                strategy.enabled = True
                strategy.schedule_next()
                self._apply_strategy_to_record(strategy, record)
        return asdict(strategy)

    async def stop_strategy(self, label: str) -> Dict[str, Any]:
        async with self.session_maker() as session:
            async with session.begin():
                repo = StrategyRepository(session, self.wallet.tenant_id)
                record = await repo.get_by_label(label)
                if not record:
                    raise WalletError(f"Strategy '{label}' not found")
                strategy = self._record_to_strategy(record)
                strategy.enabled = False
                self._apply_strategy_to_record(strategy, record)
        return asdict(strategy)

    async def delete_strategy(self, label: str) -> Dict[str, Any]:
        async with self.session_maker() as session:
            async with session.begin():
                repo = StrategyRepository(session, self.wallet.tenant_id)
                record = await repo.delete_strategy(label)
                if not record:
                    raise WalletError(f"Strategy '{label}' not found")
                strategy = self._record_to_strategy(record)
        return {"deleted": label, "strategy": asdict(strategy)}

    async def strategy_status(self, label: str) -> Dict[str, Any]:
        async with self.session_maker() as session:
            repo = StrategyRepository(session, self.wallet.tenant_id)
            record = await repo.get_by_label(label)
        if not record:
            raise WalletError(f"Strategy '{label}' not found")
        return asdict(self._record_to_strategy(record))

    async def tick_strategy(
        self,
        label: str,
        *,
        dry_run: bool = False,
        confirmation_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        lock = self._get_lock(label)
        async with lock:
            async with self.session_maker() as session:
                async with session.begin():
                    repo = StrategyRepository(session, self.wallet.tenant_id)
                    run_repo = StrategyRunRepository(session, self.wallet.tenant_id)
                    record = await repo.get_by_label(label)
                    if not record:
                        raise WalletError(f"Strategy '{label}' not found")
                    strategy = self._record_to_strategy(record)
                    if not strategy.enabled:
                        return {"action": "paused", "strategy": asdict(strategy)}

                    now = _utcnow()
                    strategy.reset_daily_if_needed(now)

                    if not strategy.due(now):
                        seconds = 0.0
                        if strategy.next_run_at:
                            try:
                                nxt = datetime.fromisoformat(strategy.next_run_at)
                                if nxt.tzinfo is None and now.tzinfo is not None:
                                    nxt = nxt.replace(tzinfo=now.tzinfo)
                                elif nxt.tzinfo is not None and now.tzinfo is None:
                                    now = now.replace(tzinfo=nxt.tzinfo)
                                seconds = max((nxt - now).total_seconds(), 0.0)
                            except ValueError:
                                seconds = 0.0
                        self._apply_strategy_to_record(strategy, record)
                        return {"action": "wait", "seconds": seconds, "strategy": asdict(strategy)}

                    if strategy.max_base_fee_gwei is not None:
                        latest = await self.wallet.web3.get_block_latest()
                        base_fee = latest.get("baseFeePerGas") or 0
                        base_fee_gwei = float(self.wallet.web3.from_wei(base_fee, "gwei"))
                        if base_fee_gwei > strategy.max_base_fee_gwei:
                            strategy.schedule_next(now)
                            self._apply_strategy_to_record(strategy, record)
                            return {
                                "action": "wait",
                                "reason": "gas_above_threshold",
                                "base_fee_gwei": base_fee_gwei,
                                "strategy": asdict(strategy),
                            }

                    sim = await self.wallet.simulate_transfer(
                        strategy.agent_id, strategy.to_address, strategy.amount_eth
                    )
                    if sim.get("insufficient_funds"):
                        strategy.schedule_next(now)
                        self._apply_strategy_to_record(strategy, record)
                        return {
                            "action": "abort",
                            "reason": "insufficient_funds",
                            "simulation": sim,
                            "strategy": asdict(strategy),
                        }

                    if (
                        strategy.daily_cap_eth is not None
                        and strategy.spent_today_eth + strategy.amount_eth > strategy.daily_cap_eth
                    ):
                        strategy.schedule_next(now)
                        self._apply_strategy_to_record(strategy, record)
                        return {
                            "action": "wait",
                            "reason": "daily_cap_reached",
                            "strategy": asdict(strategy),
                        }

                    if dry_run:
                        strategy.schedule_next(now)
                        self._apply_strategy_to_record(strategy, record)
                        return {
                            "action": "simulation",
                            "simulation": sim,
                            "strategy": asdict(strategy),
                        }

                    tx_hash = await self.wallet.execute_transfer(
                        strategy.agent_id,
                        strategy.to_address,
                        strategy.amount_eth,
                        confirmation_code=confirmation_code,
                    )
                    strategy.last_tx_hash = tx_hash
                    strategy.last_run_at = now.isoformat()
                    strategy.spent_today_eth += strategy.amount_eth
                    strategy.schedule_next(now)
                    self._apply_strategy_to_record(strategy, record)
                    await run_repo.add_run(
                        strategy_id=record.id,
                        result="sent",
                        tx_hash=tx_hash,
                        detail={"amount_eth": strategy.amount_eth},
                    )
                    return {
                        "action": "sent",
                        "tx_hash": tx_hash,
                        "strategy": asdict(strategy),
                    }
