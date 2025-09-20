from __future__ import annotations

from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from typing import Any, Optional

from .db.repositories import EventRepository
from .policy import PolicyConfig, PolicyEngine


class EventModel(BaseModel):
    id: str
    occurred_at: str
    tool_name: str
    agent_id: Optional[str]
    status: str
    request_payload: Optional[dict[str, Any]]
    response_payload: Optional[dict[str, Any]]
    error_message: Optional[str]


class PolicyModel(BaseModel):
    default_rate_limit: dict[str, Any]
    tool_overrides: dict[str, dict[str, Any]]


def create_app(policy_engine: PolicyEngine) -> FastAPI:
    app = FastAPI(title="VaultPilot Admin API", version="0.1")

    def get_policy_engine() -> PolicyEngine:
        return policy_engine

    async def get_event_repo(engine: PolicyEngine = Depends(get_policy_engine)) -> EventRepository:
        session = engine._session_maker()  # type: ignore[attr-defined]
        try:
            repo = EventRepository(session)
            yield repo
        finally:
            await session.close()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/events", response_model=list[EventModel])
    async def list_events(
        limit: int = Query(default=100, ge=1, le=1000),
        repo: EventRepository = Depends(get_event_repo),
    ) -> list[EventModel]:
        records = await repo.list_events(limit)
        return [
            EventModel(
                id=rec.id,
                occurred_at=rec.occurred_at.isoformat() if rec.occurred_at else "",
                tool_name=rec.tool_name,
                agent_id=rec.agent_id,
                status=rec.status,
                request_payload=rec.request_payload,
                response_payload=rec.response_payload,
                error_message=rec.error_message,
            )
            for rec in records
        ]

    @app.get("/policies", response_model=PolicyModel)
    async def get_policies(engine: PolicyEngine = Depends(get_policy_engine)) -> PolicyModel:
        cfg = engine.config
        return PolicyModel(
            default_rate_limit={
                "max_calls": cfg.default_rate_limit.max_calls,
                "window_seconds": cfg.default_rate_limit.window_seconds,
            },
            tool_overrides={
                k: {"max_calls": rule.max_calls, "window_seconds": rule.window_seconds}
                for k, rule in cfg.tool_overrides.items()
            },
        )

    return app

