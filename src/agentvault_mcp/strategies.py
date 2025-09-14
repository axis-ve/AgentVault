"""Stateless strategy helpers exposed via MCP tools (Phase 1).

These combine existing primitives (simulate, gas checks, execute) to provide
safe, composable flows without storing long‑lived strategy state.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone

from .wallet import AgentWalletManager


async def send_when_gas_below(
    wallet: AgentWalletManager,
    agent_id: str,
    to_address: str,
    amount_eth: float,
    max_base_fee_gwei: float,
    *,
    dry_run: bool = False,
    confirmation_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Send when base fee per gas <= threshold.

    Returns a dict with keys: action ('sent'|'wait'|'simulation'),
    base_fee_gwei, and either tx_hash or simulation.
    """
    latest = await wallet.web3.w3.eth.get_block("latest")
    base_fee_wei = latest.get("baseFeePerGas") or 0
    base_fee_gwei = float(wallet.web3.w3.from_wei(base_fee_wei, "gwei"))
    if base_fee_gwei > max_base_fee_gwei:
        return {
            "action": "wait",
            "base_fee_gwei": base_fee_gwei,
            "max_base_fee_gwei": max_base_fee_gwei,
            "reason": "gas_above_threshold",
        }

    if dry_run:
        sim = await wallet.simulate_transfer(agent_id, to_address, amount_eth)
        return {"action": "simulation", "base_fee_gwei": base_fee_gwei, "simulation": sim}

    tx_hash = await wallet.execute_transfer(
        agent_id, to_address, amount_eth, confirmation_code
    )
    return {"action": "sent", "base_fee_gwei": base_fee_gwei, "tx_hash": tx_hash}


async def dca_once(
    wallet: AgentWalletManager,
    agent_id: str,
    to_address: str,
    amount_eth: float,
    *,
    max_base_fee_gwei: Optional[float] = None,
    dry_run: bool = False,
    confirmation_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform a single DCA transfer if safe.

    - Optional gas ceiling via max_base_fee_gwei
    - Always simulate first to detect insufficient_funds
    - Dry-run returns simulation only
    """
    if max_base_fee_gwei is not None:
        latest = await wallet.web3.w3.eth.get_block("latest")
        base_fee_wei = latest.get("baseFeePerGas") or 0
        base_fee_gwei = float(wallet.web3.w3.from_wei(base_fee_wei, "gwei"))
        if base_fee_gwei > max_base_fee_gwei:
            return {
                "action": "wait",
                "reason": "gas_above_threshold",
                "base_fee_gwei": base_fee_gwei,
                "max_base_fee_gwei": max_base_fee_gwei,
            }

    sim = await wallet.simulate_transfer(agent_id, to_address, amount_eth)
    if sim.get("insufficient_funds"):
        return {"action": "abort", "reason": "insufficient_funds", "simulation": sim}
    if dry_run:
        return {"action": "simulation", "simulation": sim}

    tx_hash = await wallet.execute_transfer(
        agent_id, to_address, amount_eth, confirmation_code
    )
    return {"action": "sent", "tx_hash": tx_hash}

async def scheduled_send_once(
    wallet: AgentWalletManager,
    agent_id: str,
    to_address: str,
    amount_eth: float,
    send_at_iso: str,
    *,
    dry_run: bool = False,
    confirmation_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Send at or after a specific ISO8601 timestamp (UTC recommended)."""
    try:
        due_at = datetime.fromisoformat(send_at_iso)
    except Exception:
        return {"action": "abort", "reason": "invalid_datetime"}
    now = datetime.now(timezone.utc)
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    if now < due_at:
        secs = (due_at - now).total_seconds()
        return {"action": "wait", "seconds": secs}
    if dry_run:
        sim = await wallet.simulate_transfer(agent_id, to_address, amount_eth)
        return {"action": "simulation", "simulation": sim}
    tx_hash = await wallet.execute_transfer(
        agent_id, to_address, amount_eth, confirmation_code
    )
    return {"action": "sent", "tx_hash": tx_hash}

async def micro_tip_equal(
    wallet: AgentWalletManager,
    agent_id: str,
    recipients: list[str],
    total_amount_eth: float,
    *,
    dry_run: bool = False,
    confirmation_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Equal-split micro-tip across recipients in sequence."""
    if not recipients:
        return {"action": "abort", "reason": "no_recipients"}
    per = total_amount_eth / len(recipients)
    sims: list[Dict[str, Any]] = []
    for addr in recipients:
        sims.append(await wallet.simulate_transfer(agent_id, addr, per))
    total_fee = sum(s.get("estimated_fee_eth", 0.0) for s in sims)
    summary = {
        "recipients": recipients,
        "per_amount_eth": per,
        "estimated_fee_eth": total_fee,
        "estimated_total_eth": total_amount_eth + total_fee,
        "simulations": sims,
    }
    if dry_run:
        return {"action": "simulation", "summary": summary}
    tx_hashes: list[str] = []
    for addr in recipients:
        tx = await wallet.execute_transfer(
            agent_id, addr, per, confirmation_code
        )
        tx_hashes.append(tx)
    return {"action": "sent", "tx_hashes": tx_hashes, "summary": summary}

async def micro_tip_amounts(
    wallet: AgentWalletManager,
    agent_id: str,
    items: Dict[str, float],
    *,
    dry_run: bool = False,
    confirmation_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Micro-tip with explicit per-address ETH amounts."""
    if not items:
        return {"action": "abort", "reason": "no_recipients"}
    sims: list[Dict[str, Any]] = []
    total_amount = 0.0
    for addr, amt in items.items():
        total_amount += amt
        sims.append(await wallet.simulate_transfer(agent_id, addr, amt))
    total_fee = sum(s.get("estimated_fee_eth", 0.0) for s in sims)
    summary = {
        "items": items,
        "estimated_fee_eth": total_fee,
        "estimated_total_eth": total_amount + total_fee,
        "simulations": sims,
    }
    if dry_run:
        return {"action": "simulation", "summary": summary}
    tx_hashes: list[str] = []
    for addr, amt in items.items():
        tx = await wallet.execute_transfer(
            agent_id, addr, amt, confirmation_code
        )
        tx_hashes.append(tx)
    return {"action": "sent", "tx_hashes": tx_hashes, "summary": summary}
