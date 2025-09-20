from __future__ import annotations

from fastapi import FastAPI, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
from datetime import timedelta, datetime, timezone

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


class UsageRecord(BaseModel):
    agent_id: Optional[str]
    tool_name: str
    count: int


def create_app(policy_engine: PolicyEngine) -> FastAPI:
    app = FastAPI(title="VaultPilot Admin API", version="0.1")

    def get_policy_engine() -> PolicyEngine:
        return policy_engine

    async def get_event_repo(engine: PolicyEngine = Depends(get_policy_engine)) -> EventRepository:
        session = engine.session_maker()
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

    @app.get("/events/{event_id}", response_model=EventModel)
    async def get_event(event_id: str, repo: EventRepository = Depends(get_event_repo)) -> EventModel:
        record = await repo.get_event(event_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return EventModel(
            id=record.id,
            occurred_at=record.occurred_at.isoformat() if record.occurred_at else "",
            tool_name=record.tool_name,
            agent_id=record.agent_id,
            status=record.status,
            request_payload=record.request_payload,
            response_payload=record.response_payload,
            error_message=record.error_message,
        )

    @app.get("/events/summary", response_model=list[UsageRecord])
    async def events_summary(
        window_days: int = Query(default=1, ge=1, le=30),
        repo: EventRepository = Depends(get_event_repo),
    ) -> list[UsageRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        rows = await repo.aggregate_usage(cutoff)
        return [UsageRecord(**row) for row in rows]

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

    @app.post("/policies/reload", response_model=PolicyModel)
    async def reload_policy(engine: PolicyEngine = Depends(get_policy_engine)) -> PolicyModel:
        cfg = await engine.reload()
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
