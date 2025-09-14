"""Stateful strategy manager (Phase 2).

Provides lifecycle tools for DCA-like strategies:
 - create_strategy_dca
 - start_strategy
 - stop_strategy
 - strategy_status
 - tick_strategy

State is persisted to a JSON store (AGENTVAULT_STRATEGY_STORE). Each
strategy is identified by a unique "label" string.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from .wallet import AgentWalletManager
from . import WalletError


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    next_run_at: Optional[str] = None  # ISO8601
    last_run_at: Optional[str] = None  # ISO8601
    last_tx_hash: Optional[str] = None
    spent_day: Optional[str] = None  # YYYY-MM-DD
    spent_today_eth: float = 0.0

    def due(self, now: Optional[datetime] = None) -> bool:
        if not self.enabled:
            return False
        if not self.next_run_at:
            return True
        now = now or _utcnow()
        try:
            nxt = datetime.fromisoformat(self.next_run_at)
        except Exception:
            return True
        return now >= nxt

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
    def __init__(self, wallet: AgentWalletManager, store_path: Optional[str] = None):
        self.wallet = wallet
        path = store_path or os.getenv(
            "AGENTVAULT_STRATEGY_STORE", "agentvault_strategies.json"
        )
        self.path = Path(path).resolve()
        self._locks: Dict[str, asyncio.Lock] = {}
        self._strategies: Dict[str, DcaStrategy] = {}
        self._load()

    def _get_lock(self, label: str) -> asyncio.Lock:
        if label not in self._locks:
            self._locks[label] = asyncio.Lock()
        return self._locks[label]

    def _load(self) -> None:
        try:
            if not self.path.exists():
                return
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for label, rec in data.get("strategies", {}).items():
                try:
                    self._strategies[label] = DcaStrategy(**rec)
                except Exception:
                    continue
        except Exception:
            # Non-fatal: start with empty
            pass

    def _persist(self) -> None:
        try:
            serial = {label: asdict(s) for label, s in self._strategies.items()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"strategies": serial}, f, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            # Non-fatal persistence failure
            pass

    # -------- Public API --------
    def list_strategies(self) -> Dict[str, Dict[str, Any]]:
        return {label: asdict(s) for label, s in self._strategies.items()}

    def list_strategies_for_agent(self, agent_id: str) -> Dict[str, Dict[str, Any]]:
        return {
            label: asdict(s)
            for label, s in self._strategies.items()
            if s.agent_id == agent_id
        }

    def create_strategy_dca(
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
        if label in self._strategies:
            raise WalletError(f"Strategy '{label}' already exists")
        s = DcaStrategy(
            label=label,
            agent_id=agent_id,
            to_address=to_address,
            amount_eth=amount_eth,
            interval_seconds=interval_seconds,
            enabled=False,
            max_base_fee_gwei=max_base_fee_gwei,
            daily_cap_eth=daily_cap_eth,
        )
        self._strategies[label] = s
        self._persist()
        return asdict(s)

    def start_strategy(self, label: str) -> Dict[str, Any]:
        s = self._strategies.get(label)
        if not s:
            raise WalletError(f"Strategy '{label}' not found")
        s.enabled = True
        s.schedule_next()
        self._persist()
        return asdict(s)

    def delete_strategy(self, label: str) -> Dict[str, Any]:
        s = self._strategies.pop(label, None)
        if not s:
            raise WalletError(f"Strategy '{label}' not found")
        self._persist()
        return {"deleted": label, "strategy": asdict(s)}

    def stop_strategy(self, label: str) -> Dict[str, Any]:
        s = self._strategies.get(label)
        if not s:
            raise WalletError(f"Strategy '{label}' not found")
        s.enabled = False
        self._persist()
        return asdict(s)

    def strategy_status(self, label: str) -> Dict[str, Any]:
        s = self._strategies.get(label)
        if not s:
            raise WalletError(f"Strategy '{label}' not found")
        return asdict(s)

    async def tick_strategy(
        self,
        label: str,
        *,
        dry_run: bool = False,
        confirmation_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        s = self._strategies.get(label)
        if not s:
            raise WalletError(f"Strategy '{label}' not found")
        lock = self._get_lock(label)
        async with lock:
            if not s.enabled:
                return {"action": "paused", "strategy": asdict(s)}

            now = _utcnow()
            s.reset_daily_if_needed(now)
            if not s.due(now):
                # seconds until next
                secs = 0.0
                if s.next_run_at:
                    try:
                        nxt = datetime.fromisoformat(s.next_run_at)
                        secs = max((nxt - now).total_seconds(), 0.0)
                    except Exception:
                        pass
                return {"action": "wait", "seconds": secs, "strategy": asdict(s)}

            # Optional gas ceiling
            if s.max_base_fee_gwei is not None:
                latest = await self.wallet.web3.w3.eth.get_block("latest")
                base_fee_wei = latest.get("baseFeePerGas") or 0
                base_fee_gwei = float(
                    self.wallet.web3.w3.from_wei(base_fee_wei, "gwei")
                )
                if base_fee_gwei > s.max_base_fee_gwei:
                    # reschedule without executing
                    s.schedule_next(now)
                    self._persist()
                    return {
                        "action": "wait",
                        "reason": "gas_above_threshold",
                        "base_fee_gwei": base_fee_gwei,
                        "strategy": asdict(s),
                    }

            # Simulate for safety
            sim = await self.wallet.simulate_transfer(
                s.agent_id, s.to_address, s.amount_eth
            )
            if sim.get("insufficient_funds"):
                # reschedule and report
                s.schedule_next(now)
                self._persist()
                return {
                    "action": "abort",
                    "reason": "insufficient_funds",
                    "simulation": sim,
                    "strategy": asdict(s),
                }

            # Daily cap check
            if s.daily_cap_eth is not None and (
                s.spent_today_eth + s.amount_eth > s.daily_cap_eth
            ):
                s.schedule_next(now)
                self._persist()
                return {
                    "action": "wait",
                    "reason": "daily_cap_reached",
                    "strategy": asdict(s),
                }

            if dry_run:
                s.schedule_next(now)
                self._persist()
                return {
                    "action": "simulation",
                    "simulation": sim,
                    "strategy": asdict(s),
                }

            # Execute
            tx_hash = await self.wallet.execute_transfer(
                s.agent_id, s.to_address, s.amount_eth, confirmation_code
            )
            s.last_tx_hash = tx_hash
            s.last_run_at = now.isoformat()
            s.spent_today_eth += s.amount_eth
            s.schedule_next(now)
            self._persist()
            return {
                "action": "sent",
                "tx_hash": tx_hash,
                "strategy": asdict(s),
            }
