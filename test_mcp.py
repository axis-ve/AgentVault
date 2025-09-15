import pytest
from cryptography.fernet import Fernet

from agentvault_mcp.core import ContextManager
from agentvault_mcp.wallet import AgentWalletManager

@pytest.mark.asyncio
async def test_context_trim():
    mgr = ContextManager(max_tokens=10, trim_strategy="recency")
    # Append many large messages; trim should happen internally
    for _ in range(6):
        await mgr.append_to_history("user", "a" * 200)
    # After trimming, history should be reduced
    assert len(mgr.schema.history) < 6

@pytest.mark.asyncio
async def test_wallet_spin_up():
    class DummyEth:
        @property
        def chain_id(self):
            async def _coro():
                return 11155111
            return _coro()

    class DummyW3:
        eth = DummyEth()
        def is_address(self, addr: str) -> bool:
            return isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42

    class DummyWeb3Adapter:
        def __init__(self):
            self.w3 = DummyW3()
        async def ensure_connection(self):
            return True

    context_mgr = ContextManager()
    web3_adapter = DummyWeb3Adapter()
    encrypt_key = Fernet.generate_key().decode()
    wallet_mgr = AgentWalletManager(context_mgr, web3_adapter, encrypt_key)
    address = await wallet_mgr.spin_up_wallet("test_agent")
    assert address.startswith("0x")
    assert "test_agent_wallet" in context_mgr.schema.state

@pytest.mark.asyncio
async def test_spend_limit_gate(monkeypatch):
    class W3Stub:
        def __init__(self):
            class Eth:
                async def get_transaction_count(self, *_): return 0
                async def get_block(self, *_): return {"baseFeePerGas": 1000}
                async def estimate_gas(self, *_): return 21000
                async def wait_for_transaction_receipt(self, *_): return type("R", (), {"status": 1})
                async def get_balance(self, *_): return 10**18  # 1 ETH
                @property
                async def max_priority_fee(self): return 1000
                async def send_raw_transaction(self, *_): return b"\x12"
            self.eth = Eth()
        def is_address(self, a): return True
        def to_wei(self, v, *_): return int(v * 10**18)
        def from_wei(self, v, *_): return v / 10**18

    class Web3AdapterStub:
        def __init__(self): self.w3 = W3Stub()
        async def ensure_connection(self): return True
        async def get_nonce(self, *_): return 0

    context_mgr = ContextManager()
    encrypt_key = Fernet.generate_key().decode()
    mgr = AgentWalletManager(context_mgr, Web3AdapterStub(), encrypt_key)
    aid = "agent_limit"
    await mgr.spin_up_wallet(aid)
    # Gate above threshold
    import os
    os.environ["AGENTVAULT_MAX_TX_ETH"] = "0.1"
    with pytest.raises(Exception):
        await mgr.execute_transfer(aid, "0x" + "1"*40, 0.2)
    # Allow with correct code
    os.environ["AGENTVAULT_TX_CONFIRM_CODE"] = "ok"
    await mgr.execute_transfer(aid, "0x" + "1"*40, 0.2, confirmation_code="ok")

@pytest.mark.asyncio
async def test_keystore_export_roundtrip():
    class Web3AdapterStub:
        class _W3: eth = type("E", (), {"chain_id": 11155111})
        w3 = _W3()
        async def ensure_connection(self): return True

    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    mgr = AgentWalletManager(ctx, Web3AdapterStub(), key)
    aid = "k1"
    await mgr.spin_up_wallet(aid)
    ks = await mgr.export_wallet_keystore(aid, "pass")
    assert "\"crypto\"" in ks


@pytest.mark.asyncio
async def test_generate_response_with_fake_adapter():
    # Arrange
    class FakeAdapter:
        async def call(self, context):
            return "ok"

    mgr = ContextManager(max_tokens=100, trim_strategy="recency")
    mgr.register_adapter("fake", FakeAdapter())
    # Act
    reply = await mgr.generate_response("hello", adapter_name="fake")
    # Assert
    assert reply == "ok"
    # History should contain both user and assistant messages
    roles = [m["role"] for m in mgr.schema.history]
    assert roles.count("user") == 1 and roles.count("assistant") == 1
import os
import sys

# Allow running directly via `python test_mcp.py` without installing pkg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
