from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .. import WalletError
from .cli import upgrade
from .engine import get_session_maker
from .repositories import StrategyRepository, WalletRepository


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def import_legacy_data(
    *,
    wallet_store: Path | None,
    strategy_store: Path | None,
    database_url: str | None = None,
) -> Dict[str, int]:
    """Import legacy JSON stores into the VaultPilot database."""

    upgrade(database_url)
    session_maker = get_session_maker(database_url)
    summary = {
        "wallets_imported": 0,
        "wallets_skipped": 0,
        "strategies_imported": 0,
        "strategies_skipped": 0,
    }

    if wallet_store is not None and wallet_store.exists():
        data = _load_json(wallet_store)
        async def _import_wallets() -> None:
            async with session_maker() as session:
                async with session.begin():
                    repo = WalletRepository(session)
                    for agent_id, rec in data.items():
                        encrypted_hex = rec.get("encrypted_privkey_hex")
                        if not encrypted_hex:
                            summary["wallets_skipped"] += 1
                            continue
                        await repo.upsert_wallet(
                            agent_id=agent_id,
                            address=rec["address"],
                            encrypted_privkey=bytes.fromhex(encrypted_hex),
                            chain_id=int(rec.get("chain_id", 0)),
                            last_nonce=rec.get("last_nonce"),
                            metadata_json={},
                        )
                        summary["wallets_imported"] += 1
        import asyncio
        asyncio.run(_import_wallets())

    if strategy_store is not None and strategy_store.exists():
        raw = _load_json(strategy_store)
        strategies = raw.get("strategies", {})

        def _parse_dt(value: str | None) -> datetime | None:
            if not value:
                return None
            return datetime.fromisoformat(value)

        async def _import_strategies() -> None:
            async with session_maker() as session:
                async with session.begin():
                    repo = StrategyRepository(session)
                    for label, rec in strategies.items():
                        if await repo.get_by_label(label):
                            summary["strategies_skipped"] += 1
                            continue
                        spent_day = rec.get("spent_day")
                        spent_dt = datetime.fromisoformat(spent_day).date() if spent_day else None
                        await repo.create_strategy(
                            label=label,
                            agent_id=rec["agent_id"],
                            strategy_type="dca",
                            to_address=rec["to_address"],
                            amount_eth=float(rec["amount_eth"]),
                            interval_seconds=int(rec["interval_seconds"]),
                            enabled=bool(rec.get("enabled", False)),
                            max_base_fee_gwei=rec.get("max_base_fee_gwei"),
                            daily_cap_eth=rec.get("daily_cap_eth"),
                            next_run_at=_parse_dt(rec.get("next_run_at")),
                            last_run_at=_parse_dt(rec.get("last_run_at")),
                            last_tx_hash=rec.get("last_tx_hash"),
                            spent_day=spent_dt,
                            spent_today_eth=float(rec.get("spent_today_eth", 0.0)),
                            config={},
                        )
                        summary["strategies_imported"] += 1
        import asyncio
        asyncio.run(_import_strategies())

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Import legacy AgentVault JSON stores into the database")
    parser.add_argument("--wallet-store", type=Path, default=Path("agentvault_store.json"))
    parser.add_argument("--strategy-store", type=Path, default=Path("agentvault_strategies.json"))
    parser.add_argument("--database-url")
    args = parser.parse_args()

    summary = import_legacy_data(
        wallet_store=args.wallet_store,
        strategy_store=args.strategy_store,
        database_url=args.database_url,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
