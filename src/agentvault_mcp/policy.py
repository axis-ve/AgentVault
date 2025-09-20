from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from .db.repositories import EventRepository

DEFAULT_POLICY_PATH = "vaultpilot_policy.yml"


@dataclass
class RateLimitRule:
    max_calls: int
    window_seconds: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RateLimitRule":
        return cls(
            max_calls=int(data.get("max_calls", 60)),
            window_seconds=int(data.get("window_seconds", 60)),
        )


@dataclass
class PolicyConfig:
    default_rate_limit: RateLimitRule
    tool_overrides: Dict[str, RateLimitRule]

    @classmethod
    def load(cls, path: Optional[str] = None) -> "PolicyConfig":
        path_obj = Path(path or os.getenv("VAULTPILOT_POLICY_PATH", DEFAULT_POLICY_PATH))
        if not path_obj.exists():
            return cls(
                default_rate_limit=RateLimitRule(max_calls=120, window_seconds=60),
                tool_overrides={},
            )
        with path_obj.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        rate_limits = raw.get("rate_limits", {})
        default_rule = RateLimitRule.from_dict(rate_limits.get("default", {}))
        overrides: Dict[str, RateLimitRule] = {}
        for tool, rule in (rate_limits.get("tools", {}) or {}).items():
            overrides[tool] = RateLimitRule.from_dict(rule)
        return cls(default_rate_limit=default_rule, tool_overrides=overrides)

    def rule_for(self, tool_name: str) -> RateLimitRule:
        return self.tool_overrides.get(tool_name, self.default_rate_limit)


class PolicyEngine:
    def __init__(self, session_maker, config: PolicyConfig) -> None:
        self._session_maker = session_maker
        self._config = config
        self._lock = asyncio.Lock()

    @property
    def config(self) -> PolicyConfig:
        return self._config

    @property
    def session_maker(self):
        return self._session_maker

    async def _count_recent_events(
        self, tool_name: str, agent_id: Optional[str], window: timedelta
    ) -> int:
        cutoff = datetime.now(timezone.utc) - window
        async with self._session_maker() as session:
            repo = EventRepository(session)
            return await repo.count_events_since(tool_name, agent_id, cutoff)

    async def enforce(
        self,
        *,
        tool_name: str,
        agent_id: Optional[str],
    ) -> None:
        if agent_id is None:
            return
        rule = self._config.rule_for(tool_name)
        if rule.max_calls <= 0:
            return
        async with self._lock:
            recent = await self._count_recent_events(
                tool_name, agent_id, timedelta(seconds=rule.window_seconds)
            )
            if recent >= rule.max_calls:
                raise PermissionError(
                    f"Rate limit exceeded for tool '{tool_name}' (agent={agent_id})"
                )

    async def record_event(
        self,
        *,
        tool_name: str,
        agent_id: Optional[str],
        status: str,
        request_payload: Dict[str, Any] | None,
        response_payload: Dict[str, Any] | None,
        error_message: str | None = None,
    ) -> None:
        async with self._session_maker() as session:
            async with session.begin():
                repo = EventRepository(session)
                await repo.record_event(
                    tool_name=tool_name,
                    agent_id=agent_id,
                    status=status,
                    request_payload=request_payload,
                    response_payload=response_payload,
                    error_message=error_message,
                )


def extract_agent_id(kwargs: Dict[str, Any]) -> Optional[str]:
    for key in ("agent_id", "agent", "address"):
        if key in kwargs and isinstance(kwargs[key], str):
            return kwargs[key]
    return None


async def run_with_policy(
    engine: PolicyEngine,
    *,
    tool_name: str,
    agent_id: Optional[str],
    request_payload: Dict[str, Any] | None,
    call: Callable[[], Any],
) -> Any:
    await engine.enforce(tool_name=tool_name, agent_id=agent_id)
    try:
        result = await call()
        response = result
        if isinstance(result, (str, bytes)):
            response = {"result": result if isinstance(result, str) else result.decode()}
        await engine.record_event(
            tool_name=tool_name,
            agent_id=agent_id,
            status="ok",
            request_payload=request_payload,
            response_payload=response,
        )
        return result
    except Exception as exc:  # pragma: no cover - re-raised for tests
        await engine.record_event(
            tool_name=tool_name,
            agent_id=agent_id,
            status="error",
            request_payload=request_payload,
            response_payload=None,
            error_message=str(exc),
        )
        raise
