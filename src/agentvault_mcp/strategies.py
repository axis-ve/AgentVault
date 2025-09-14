"""Stateless strategy helpers exposed via MCP tools (Phase 1).

These combine existing primitives (simulate, gas checks, execute) to provide
safe, composable flows without storing long‑lived strategy state.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

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

