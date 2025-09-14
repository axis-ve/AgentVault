import os
import pytest
from cryptography.fernet import Fernet

from agentvault_mcp.core import ContextManager
from agentvault_mcp.wallet import AgentWalletManager
from agentvault_mcp.strategy_manager import StrategyManager


class _Web3:
    class Eth:
        async def get_block(self, *_):
            return {"baseFeePerGas": 1 * 10**9}

    eth = Eth()

    def from_wei(self, v, unit):
        if unit == "gwei":
            return v / 10**9
        if unit == "ether":
            return v / 10**18
        return v


class _Web3Adapter:
    def __init__(self):
        self.w3 = _Web3()

    async def ensure_connection(self):
        return True

    async def get_nonce(self, *_):
        return 0


@pytest.mark.asyncio
async def test_strategy_lifecycle(tmp_path):
    # Wallet manager with stub web3
    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    web3 = _Web3Adapter()
    mgr = AgentWalletManager(ctx, web3, key, persist_path=str(tmp_path / "store.json"))
    await mgr.spin_up_wallet("agent")

    # Monkeypatch wallet methods to avoid RPC heavy ops
    async def fake_sim(agent_id, to, amt):
        return {"insufficient_funds": False}

    async def fake_exec(agent_id, to, amt, code=None):
        return "0xabc"

    mgr.simulate_transfer = fake_sim  # type: ignore
    mgr.execute_transfer = fake_exec  # type: ignore

    strat_path = str(tmp_path / "strategies.json")
    sm = StrategyManager(mgr, store_path=strat_path)
    s = sm.create_strategy_dca(
        label="dca1",
        agent_id="agent",
        to_address="0x" + "1" * 40,
        amount_eth=0.001,
        interval_seconds=1,
        max_base_fee_gwei=100.0,
        daily_cap_eth=0.01,
    )
    assert s["label"] == "dca1"

    s = sm.start_strategy("dca1")
    assert s["enabled"] is True

    res = await sm.tick_strategy("dca1", dry_run=True)
    assert res["action"] == "simulation"

    res = await sm.tick_strategy("dca1")
    assert res["action"] == "sent"
    assert res["tx_hash"] == "0xabc"

    s = sm.stop_strategy("dca1")
    assert s["enabled"] is False
    res = await sm.tick_strategy("dca1")
    assert res["action"] == "paused"

