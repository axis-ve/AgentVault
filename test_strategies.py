import os
import pytest

from cryptography.fernet import Fernet

from agentvault_mcp.core import ContextManager
from agentvault_mcp.wallet import AgentWalletManager
from agentvault_mcp.strategies import send_when_gas_below, dca_once
from agentvault_mcp.strategies import scheduled_send_once, micro_tip_equal, micro_tip_amounts


class _W3:
    def __init__(self, base_fee_wei: int):
        class Eth:
            def __init__(self, base_fee):
                self._base_fee = base_fee

            async def get_block(self, *_):
                return {"baseFeePerGas": self._base_fee}

        self.eth = Eth(base_fee_wei)

    def from_wei(self, v, unit):
        if unit == "gwei":
            return v / 10**9
        if unit == "ether":
            return v / 10**18
        return v


class _Web3Adapter:
    def __init__(self, base_fee_wei: int):
        self.w3 = _W3(base_fee_wei)

    async def ensure_connection(self):
        return True

    async def get_nonce(self, *_):
        return 0


@pytest.mark.asyncio
async def test_send_when_gas_below_waits():
    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    web3 = _Web3Adapter(base_fee_wei=50 * 10**9)  # 50 gwei
    mgr = AgentWalletManager(ctx, web3, key)
    await mgr.spin_up_wallet("a")
    res = await send_when_gas_below(mgr, "a", "0x" + "1" * 40, 0.001, 1.0)
    assert res["action"] == "wait"


@pytest.mark.asyncio
async def test_send_when_gas_below_simulate():
    class W3S(_W3):
        def __init__(self):
            super().__init__(base_fee_wei=1 * 10**9)

        class Eth:
            pass

    class W3A:
        def __init__(self):
            self.w3 = _W3(1 * 10**9)

        async def ensure_connection(self):
            return True

        async def get_nonce(self, *_):
            return 0

    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    mgr = AgentWalletManager(ctx, W3A(), key)
    await mgr.spin_up_wallet("b")
    # Simulate path; should return a simulation dict
    res = await send_when_gas_below(
        mgr, "b", "0x" + "1" * 40, 0.001, 10.0, dry_run=True
    )
    assert res["action"] == "simulation"
    assert "simulation" in res


@pytest.mark.asyncio
async def test_dca_once_gas_ceiling():
    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    web3 = _Web3Adapter(base_fee_wei=100 * 10**9)  # 100 gwei
    mgr = AgentWalletManager(ctx, web3, key)
    await mgr.spin_up_wallet("c")
    res = await dca_once(mgr, "c", "0x" + "1" * 40, 0.001, max_base_fee_gwei=10.0)
    assert res["action"] == "wait"


@pytest.mark.asyncio
async def test_scheduled_send_wait_then_sim():
    from datetime import datetime, timedelta, timezone

    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    web3 = _Web3Adapter(base_fee_wei=1 * 10**9)
    mgr = AgentWalletManager(ctx, web3, key)
    await mgr.spin_up_wallet("sched")
    future = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    res = await scheduled_send_once(
        mgr, "sched", "0x" + "1" * 40, 0.001, future
    )
    assert res["action"] == "wait"
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    res = await scheduled_send_once(
        mgr, "sched", "0x" + "1" * 40, 0.001, past, dry_run=True
    )
    assert res["action"] == "simulation"


@pytest.mark.asyncio
async def test_micro_tip_helpers_dry_run():
    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    web3 = _Web3Adapter(base_fee_wei=1 * 10**9)
    mgr = AgentWalletManager(ctx, web3, key)
    await mgr.spin_up_wallet("mt")
    res = await micro_tip_equal(
        mgr, "mt", ["0x" + "1" * 40, "0x" + "2" * 40], 0.01, dry_run=True
    )
    assert res["action"] == "simulation"
    res = await micro_tip_amounts(
        mgr, "mt", {"0x" + "1" * 40: 0.005, "0x" + "2" * 40: 0.005}, dry_run=True
    )
    assert res["action"] == "simulation"
import os
import sys

# Allow running directly via `python test_strategies.py` without installing pkg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
