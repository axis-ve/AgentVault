import pytest
from cryptography.fernet import Fernet

from wallet_mcp_server import ContextManager, AgentWalletManager

@pytest.mark.asyncio
async def test_context_trim():
    mgr = ContextManager(max_tokens=10, trim_strategy="recency")
    mgr.schema.history = [{"role": "user", "content": "a" * 100}] * 5  # Overflow
    await mgr._trim_context()  # Should trim without error
    assert len(mgr.schema.history) < 5

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
