from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine

_DEFAULT_DB_URL = "sqlite+aiosqlite:///vaultpilot.db"
_SYNC_SQLITE_FALLBACK = "sqlite+pysqlite:///vaultpilot.db"


def _coerce_database_url(url: Optional[str]) -> str:
    if url:
        return url
    return os.getenv("VAULTPILOT_DATABASE_URL", _DEFAULT_DB_URL)


@lru_cache
def get_async_engine(database_url: Optional[str] = None) -> AsyncEngine:
    url = _coerce_database_url(database_url)
    return create_async_engine(url, pool_pre_ping=True, future=True)


@lru_cache
def get_sync_engine(database_url: Optional[str] = None) -> Engine:
    url = _coerce_database_url(database_url)
    if url.startswith("sqlite+aiosqlite"):
        url = url.replace("sqlite+aiosqlite", "sqlite+pysqlite")
    return create_engine(url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_maker(database_url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    engine = get_async_engine(database_url)
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


__all__ = [
    "get_async_engine",
    "get_sync_engine",
    "get_session_maker",
]
