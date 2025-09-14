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
