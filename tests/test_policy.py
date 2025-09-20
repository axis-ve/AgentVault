import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet

from agentvault_mcp.core import ContextManager
from agentvault_mcp.wallet import AgentWalletManager
from agentvault_mcp.policy import PolicyConfig, PolicyEngine, RateLimitRule, run_with_policy
from agentvault_mcp.db.repositories import EventRepository


class DummyWeb3:
    class Eth:
        chain_id = 11155111

    eth = Eth()

    async def ensure_connection(self):
        return True

    async def get_nonce(self, *_):
        return 0


class DummyAdapter:
    def __init__(self):
        self.w3 = DummyWeb3()

    async def ensure_connection(self):
        return True


def _make_engine(tmp_path):
    ctx = ContextManager()
    mgr = AgentWalletManager(
        ctx,
        DummyAdapter(),
        Fernet.generate_key().decode(),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'policy.db'}",
        auto_migrate=True,
    )
    config = PolicyConfig(
        default_rate_limit=RateLimitRule(max_calls=1, window_seconds=60),
        tool_overrides={},
    )
    engine = PolicyEngine(mgr.session_maker, config)
    return engine


@pytest.mark.asyncio
async def test_policy_rate_limit(tmp_path):
    engine = _make_engine(tmp_path)

    async def call():
        return "ok"

    await run_with_policy(
        engine,
        tool_name="test_tool",
        agent_id="agent",
        request_payload={"test": True},
        call=call,
    )

    with pytest.raises(PermissionError):
        await run_with_policy(
            engine,
            tool_name="test_tool",
            agent_id="agent",
            request_payload={"test": True},
            call=call,
        )


@pytest.mark.asyncio
async def test_policy_event_logging(tmp_path):
    engine = _make_engine(tmp_path)

    async def call():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        await run_with_policy(
            engine,
            tool_name="test_tool",
            agent_id="agent",
            request_payload={"demo": 1},
            call=call,
        )

    async with engine.session_maker() as session:
        repo = EventRepository(session)
        events = await repo.list_events(10)

    assert events
    assert events[0].status == "error"
    assert events[0].error_message == "fail"

    async with engine.session_maker() as session:
        repo = EventRepository(session)
        usage = await repo.aggregate_usage(datetime.now(timezone.utc) - timedelta(days=1))

    assert usage
    assert usage[0]["count"] >= 1


@pytest.mark.asyncio
async def test_policy_reload(tmp_path, monkeypatch):
    config_path = tmp_path / "policy.yml"
    config_path.write_text(
        """rate_limits:\n  default:\n    max_calls: 1\n    window_seconds: 60\n"""
    )
    ctx = ContextManager()
    mgr = AgentWalletManager(
        ctx,
        DummyAdapter(),
        Fernet.generate_key().decode(),
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'policy_reload.db'}",
        auto_migrate=True,
    )
    config = PolicyConfig.load(config_path)
    engine = PolicyEngine(mgr.session_maker, config, config_path=str(config_path))
    assert engine.config.default_rate_limit.max_calls == 1

    config_path.write_text(
        """rate_limits:\n  default:\n    max_calls: 5\n    window_seconds: 120\n"""
    )

    await engine.reload()
    assert engine.config.default_rate_limit.max_calls == 5
    assert engine.config.default_rate_limit.window_seconds == 120
