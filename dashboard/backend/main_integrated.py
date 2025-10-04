"""
AgentVault Dashboard Backend - Integrated with MCP Server
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import jwt
import os
import sys

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

# Add parent directory to path to import agentvault_mcp
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from src.agentvault_mcp.adapters.web3_adapter import Web3Adapter
from src.agentvault_mcp.core import ContextManager
from src.agentvault_mcp.db.models import MCPEvent
from src.agentvault_mcp.db.repositories import EventRepository, WalletRepository
from src.agentvault_mcp.strategy_manager import StrategyManager
from src.agentvault_mcp.wallet import AgentWalletManager

load_dotenv()

app = FastAPI(
    title="AgentVault Dashboard API",
    description="Backend API for AgentVault - Integrated with MCP Server",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AGENTVAULT_DASHBOARD_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security / auth helpers
security = HTTPBearer(auto_error=False)
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ALLOW_ANON = os.getenv("AGENTVAULT_DASHBOARD_ALLOW_ANON", "1") == "1"

# Usage & billing constants
COST_PER_EVENT = float(os.getenv("AGENTVAULT_COST_PER_EVENT", "0.01"))
AIR_DROP_RATE = float(os.getenv("AGENTVAULT_AIRDROP_RATE", "0.05"))
MAX_EVENTS_FETCH = int(os.getenv("AGENTVAULT_MAX_EVENTS_FETCH", "1000"))

# Airdrop in-memory state (dev only)
CLAIM_STATE: Dict[str, Dict[str, Any]] = {}
CLAIM_LOCK = asyncio.Lock()

_wallet_manager: Optional[AgentWalletManager] = None
_strategy_manager: Optional[StrategyManager] = None


class User(BaseModel):
    id: str
    email: str
    wallet_address: Optional[str] = None
    token_balance: float = 0
    total_usage: int = 0
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class AgentCreate(BaseModel):
    name: str
    description: str


class Agent(BaseModel):
    id: str
    name: str
    description: str
    wallet_address: str
    balance_eth: float
    status: str
    created_at: datetime
    last_active: Optional[datetime] = None


class TransferRequest(BaseModel):
    agent_id: str
    to_address: str
    amount_eth: float
    confirmation_code: Optional[str] = None
    dry_run: bool = False


class StrategyCreate(BaseModel):
    label: str
    agent_id: str
    to_address: str
    amount_eth: float
    interval_seconds: int
    max_base_fee_gwei: Optional[float] = None
    daily_cap_eth: Optional[float] = None


class FaucetRequest(BaseModel):
    amount_eth: Optional[float] = None


# Mock user database (replace with real persistence when auth added)
MOCK_USERS = {
    "demo@agentvault.com": {
        "id": "user-demo",
        "email": "demo@agentvault.com",
        "password": "demo123",  # In production: store hashed password
    }
}


# ---------------------------------------------------------------------------
# Initialization helpers
# ---------------------------------------------------------------------------

def get_wallet_manager() -> AgentWalletManager:
    global _wallet_manager
    if _wallet_manager is None:
        ctx = ContextManager()
        rpc_url = os.getenv("WEB3_RPC_URL", "https://ethereum-sepolia.publicnode.com")
        web3_adapter = Web3Adapter(rpc_url)
        encrypt_key = os.getenv("ENCRYPT_KEY")
        if not encrypt_key:
            raise RuntimeError("ENCRYPT_KEY not set in environment")
        database_url = os.getenv("VAULTPILOT_DATABASE_URL", "sqlite+aiosqlite:///./agentvault.db")
        _wallet_manager = AgentWalletManager(
            ctx,
            web3_adapter,
            encrypt_key,
            database_url=database_url,
            tenant_id="default",
            auto_migrate=True,
        )
    return _wallet_manager


def get_strategy_manager() -> StrategyManager:
    global _strategy_manager
    if _strategy_manager is None:
        _strategy_manager = StrategyManager(get_wallet_manager())
    return _strategy_manager


async def _load_events(limit: int = MAX_EVENTS_FETCH) -> List[MCPEvent]:
    wallet_mgr = get_wallet_manager()
    async with wallet_mgr.session_maker() as session:
        repo = EventRepository(session, wallet_mgr.tenant_id)
        return await repo.list_events(limit)


def _default_user() -> dict[str, str]:
    return {"sub": "guest", "email": "guest@agentvault.local"}


def _cost_for_requests(requests: int) -> float:
    return round(requests * COST_PER_EVENT, 4)


# ---------------------------------------------------------------------------
# Auth utilities
# ---------------------------------------------------------------------------


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    if credentials is None:
        if ALLOW_ANON:
            return _default_user()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        return jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _group_daily(events: List[MCPEvent], days: int = 7) -> List[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    buckets: Dict[str, dict[str, Any]] = {}
    for offset in range(days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date().isoformat()
        buckets[day] = {"date": day, "requests": 0, "cost": 0.0}

    for event in events:
        if not event.occurred_at:
            continue
        day = event.occurred_at.astimezone(timezone.utc).date().isoformat()
        if day in buckets:
            buckets[day]["requests"] += 1

    for bucket in buckets.values():
        bucket["cost"] = _cost_for_requests(bucket["requests"])

    return list(buckets.values())


def _group_monthly(events: List[MCPEvent], months: int = 6) -> List[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    buckets: Dict[str, dict[str, Any]] = {}
    for offset in range(months - 1, -1, -1):
        month_dt = (now.replace(day=1) - timedelta(days=offset * 30))
        key = month_dt.strftime("%Y-%m")
        buckets[key] = {"month": key, "requests": 0, "cost": 0.0}

    for event in events:
        if not event.occurred_at:
            continue
        key = event.occurred_at.astimezone(timezone.utc).strftime("%Y-%m")
        if key in buckets:
            buckets[key]["requests"] += 1

    for bucket in buckets.values():
        bucket["cost"] = _cost_for_requests(bucket["requests"])

    return list(buckets.values())


def _activity_from_event(event: MCPEvent) -> dict[str, Any]:
    tool = event.tool_name or "unknown"
    status = event.status
    description = ""
    if tool.startswith("execute_transfer"):
        activity_type = "transaction"
        description = "Transfer executed via MCP"
    elif "strategy" in tool:
        activity_type = "strategy"
        description = f"Strategy call: {tool}"
    elif tool.startswith("spin_up_wallet"):
        activity_type = "agent_created"
        description = "New wallet provisioned"
    else:
        activity_type = "tool_call"
        description = f"Tool invoked: {tool}"

    if status == "error" and event.error_message:
        description = event.error_message[:200]

    return {
        "id": event.id,
        "type": activity_type,
        "title": tool,
        "description": description,
        "timestamp": (event.occurred_at or datetime.now(timezone.utc)).isoformat(),
        "status": "success" if status == "ok" else ("error" if status == "error" else "pending"),
    }


async def _generate_airdrop_claims(total_requests: int) -> List[dict[str, Any]]:
    if total_requests < 25:
        return []
    async with CLAIM_LOCK:
        amount = round(total_requests * AIR_DROP_RATE * COST_PER_EVENT, 4)
        claim_id = "usage-bonus"
        existing = CLAIM_STATE.get(claim_id)
        if not existing:
            deadline = datetime.now(timezone.utc) + timedelta(days=14)
            CLAIM_STATE[claim_id] = {
                "id": claim_id,
                "amount": amount,
                "status": "available",
                "claimDeadline": deadline.isoformat(),
                "description": "Monthly usage reward",
            }
        else:
            existing["amount"] = amount
        return list(CLAIM_STATE.values())


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/auth/login")
async def login(email: str, password: str):
    user_data = MOCK_USERS.get(email)
    if not user_data or password != user_data["password"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user_data["id"], "email": user_data["email"]})
    return {
        "access_token": token,
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "token_balance": 0.0,
            "total_usage": 0,
        },
    }


# ---------------------------------------------------------------------------
# Dashboard endpoints
# ---------------------------------------------------------------------------


@app.get("/")
async def root():
    return {
        "message": "AgentVault Dashboard API - Integrated",
        "version": app.version,
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    wallet_mgr = get_wallet_manager()
    db_status = "healthy"
    web3_status = "healthy"

    try:
        async with wallet_mgr.session_maker() as session:
            repo = WalletRepository(session, wallet_mgr.tenant_id)
            await repo.list_wallets()
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    try:
        await wallet_mgr.provider_status()
    except Exception as exc:
        web3_status = f"unhealthy: {exc}"

    healthy = db_status == "healthy" and web3_status == "healthy"
    return {
        "status": "healthy" if healthy else "unhealthy",
        "database": db_status,
        "web3": web3_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/dashboard/stats")
async def get_dashboard_stats(token_data: dict = Depends(verify_token)):
    wallet_mgr = get_wallet_manager()
    strategy_mgr = get_strategy_manager()

    async with wallet_mgr.session_maker() as session:
        wallet_repo = WalletRepository(session, wallet_mgr.tenant_id)
        wallet_records = await wallet_repo.list_wallets()

    wallets_summary = []
    for record in wallet_records:
        try:
            balance = await wallet_mgr.query_balance(record.agent_id)
        except Exception:
            balance = 0.0
        wallets_summary.append({"agent_id": record.agent_id, "address": record.address, "balance": balance})

    strategies = await strategy_mgr.list_strategies()
    active_strategies = sum(1 for strat in strategies.values() if strat.get("enabled"))

    events = await _load_events()
    total_usage = len(events)
    last_30_days = [e for e in events if e.occurred_at and e.occurred_at >= datetime.now(timezone.utc) - timedelta(days=30)]
    monthly_usage = len(last_30_days)

    provider_info = {}
    try:
        provider_info = await wallet_mgr.provider_status()
    except Exception:
        provider_info = {}

    token_balance = sum(entry["balance"] for entry in wallets_summary)

    next_airdrop = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    return {
        "totalAgents": len(wallet_records),
        "activeAgents": sum(1 for entry in wallets_summary if entry["balance"] > 0),
        "totalUsage": total_usage,
        "monthlyUsage": monthly_usage,
        "tokenBalance": f"{token_balance:.4f}",
        "airdropEligible": monthly_usage >= 25,
        "nextAirdrop": next_airdrop,
        "chainId": provider_info.get("chain_id"),
        "latestBlock": provider_info.get("latest_block_number"),
        "gasPrice": provider_info.get("estimated_gas_price_gwei"),
        "activeStrategies": active_strategies,
    }


@app.get("/agents")
async def get_agents(token_data: dict = Depends(verify_token)) -> List[Agent]:
    wallet_mgr = get_wallet_manager()
    async with wallet_mgr.session_maker() as session:
        wallet_repo = WalletRepository(session, wallet_mgr.tenant_id)
        wallet_records = await wallet_repo.list_wallets()

    agents: List[Agent] = []
    for record in wallet_records:
        try:
            balance = await wallet_mgr.query_balance(record.agent_id)
        except Exception:
            balance = 0.0
        agents.append(
            Agent(
                id=record.agent_id,
                name=record.agent_id,
                description=f"Agent wallet {record.address[:10]}...",
                wallet_address=record.address,
                balance_eth=balance,
                status="active" if balance > 0 else "idle",
                created_at=record.created_at or datetime.now(timezone.utc),
                last_active=record.updated_at,
            )
        )
    return agents


@app.post("/agents/create")
async def create_agent(agent_data: AgentCreate, token_data: dict = Depends(verify_token)):
    wallet_mgr = get_wallet_manager()
    agent_id = agent_data.name.strip().lower().replace(" ", "-") or f"agent-{uuid4().hex[:8]}"
    try:
        address = await wallet_mgr.spin_up_wallet(agent_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating agent: {exc}")
    return {
        "id": agent_id,
        "name": agent_data.name,
        "description": agent_data.description,
        "wallet_address": address,
        "status": "created",
        "message": "Agent wallet created successfully",
    }


@app.get("/agents/{agent_id}/balance")
async def get_agent_balance(agent_id: str, token_data: dict = Depends(verify_token)):
    wallet_mgr = get_wallet_manager()
    try:
        balance = await wallet_mgr.query_balance(agent_id)
        return {"agent_id": agent_id, "balance_eth": balance}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Agent not found: {exc}")


@app.post("/agents/transfer")
async def execute_transfer(transfer: TransferRequest, token_data: dict = Depends(verify_token)):
    wallet_mgr = get_wallet_manager()
    try:
        simulation = await wallet_mgr.simulate_transfer(
            transfer.agent_id,
            transfer.to_address,
            transfer.amount_eth,
        )
        if simulation.get("insufficient_funds"):
            raise HTTPException(status_code=400, detail="Insufficient funds for amount + fees")

        if transfer.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "simulation": simulation,
            }

        tx_hash = await wallet_mgr.execute_transfer(
            transfer.agent_id,
            transfer.to_address,
            transfer.amount_eth,
            confirmation_code=transfer.confirmation_code,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transfer failed: {exc}")
    return {
        "success": True,
        "tx_hash": tx_hash,
        "amount_eth": transfer.amount_eth,
        "to_address": transfer.to_address,
        "estimated_fee_eth": simulation.get("estimated_fee_eth"),
    }


@app.post("/agents/{agent_id}/faucet")
async def request_faucet(agent_id: str, faucet: FaucetRequest, token_data: dict = Depends(verify_token)):
    wallet_mgr = get_wallet_manager()
    try:
        result = await wallet_mgr.request_faucet_funds(
            agent_id,
            amount_eth=faucet.amount_eth,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Faucet request failed: {exc}")


@app.get("/strategies")
async def get_strategies(token_data: dict = Depends(verify_token)):
    strategy_mgr = get_strategy_manager()
    try:
        return await strategy_mgr.list_strategies()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error fetching strategies: {exc}")


@app.post("/strategies/create")
async def create_strategy(strategy: StrategyCreate, token_data: dict = Depends(verify_token)):
    strategy_mgr = get_strategy_manager()
    try:
        return await strategy_mgr.create_strategy_dca(
            label=strategy.label,
            agent_id=strategy.agent_id,
            to_address=strategy.to_address,
            amount_eth=strategy.amount_eth,
            interval_seconds=strategy.interval_seconds,
            max_base_fee_gwei=strategy.max_base_fee_gwei,
            daily_cap_eth=strategy.daily_cap_eth,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error creating strategy: {exc}")


@app.post("/strategies/{label}/start")
async def start_strategy(label: str, token_data: dict = Depends(verify_token)):
    strategy_mgr = get_strategy_manager()
    try:
        return await strategy_mgr.start_strategy(label)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error starting strategy: {exc}")


@app.post("/strategies/{label}/stop")
async def stop_strategy(label: str, token_data: dict = Depends(verify_token)):
    strategy_mgr = get_strategy_manager()
    try:
        return await strategy_mgr.stop_strategy(label)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error stopping strategy: {exc}")


@app.post("/strategies/{label}/tick")
async def tick_strategy(label: str, token_data: dict = Depends(verify_token)):
    strategy_mgr = get_strategy_manager()
    try:
        return await strategy_mgr.tick_strategy(label, dry_run=False)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error ticking strategy: {exc}")


@app.get("/usage")
async def get_usage_stats(token_data: dict = Depends(verify_token)):
    events = await _load_events()
    total_requests = len(events)
    total_cost = _cost_for_requests(total_requests)
    daily_usage = _group_daily(events, days=7)
    monthly_usage = _group_monthly(events, months=6)
    return {
        "total_requests": total_requests,
        "total_cost": total_cost,
        "daily_usage": daily_usage,
        "monthly_usage": monthly_usage,
    }


@app.get("/billing/history")
async def get_billing_history(token_data: dict = Depends(verify_token)):
    usage = await get_usage_stats(token_data=token_data)
    history: List[dict[str, Any]] = []
    for month in usage["monthly_usage"]:
        if month["requests"] == 0:
            continue
        timestamp = datetime.strptime(month["month"], "%Y-%m").replace(tzinfo=timezone.utc)
        history.append(
            {
                "id": f"invoice-{month['month']}",
                "amount": round(month["cost"], 4),
                "description": f"AgentVault usage for {month['month']}",
                "timestamp": timestamp.isoformat(),
                "status": "paid" if timestamp < datetime.now(timezone.utc).replace(day=1) else "pending",
            }
        )
    return history


@app.get("/activity/recent")
async def get_recent_activity(token_data: dict = Depends(verify_token)):
    events = await _load_events(limit=50)
    return [_activity_from_event(event) for event in events[:10]]


@app.get("/airdrops/claims")
async def list_airdrop_claims(token_data: dict = Depends(verify_token)):
    usage = await get_usage_stats(token_data=token_data)
    claims = await _generate_airdrop_claims(usage["monthly_usage"][-1]["requests"] if usage["monthly_usage"] else 0)
    return claims


@app.post("/airdrops/claim/{claim_id}")
async def claim_airdrop(claim_id: str, token_data: dict = Depends(verify_token)):
    async with CLAIM_LOCK:
        claim = CLAIM_STATE.get(claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        if claim.get("status") != "available":
            raise HTTPException(status_code=400, detail="Claim already processed")
        claim["status"] = "claimed"
        claim["claimedAt"] = datetime.now(timezone.utc).isoformat()
        return {"status": "claimed", "amount": claim["amount"]}


@app.get("/user/profile")
async def get_user_profile(token_data: dict = Depends(verify_token)):
    usage = await get_usage_stats(token_data=token_data)
    return {
        "id": token_data.get("sub"),
        "email": token_data.get("email"),
        "token_balance": 0.0,
        "total_usage": usage["total_requests"],
        "join_date": datetime.utcnow().isoformat(),
        "tier": "starter" if usage["total_requests"] < 100 else "pro",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("ADMIN_API_HOST", "0.0.0.0")
    port = int(os.getenv("ADMIN_API_PORT", 8000))

    print(
        f"""
╔══════════════════════════════════════════════════════════════╗
║  AgentVault Dashboard API - Integrated                      ║
║  Version: {app.version:<8}                                          ║
║                                                              ║
║  API Server: http://{host}:{port}                         ║
║  API Docs:   http://{host}:{port}/docs                    ║
║  Health:     http://{host}:{port}/health                  ║
╚══════════════════════════════════════════════════════════════╝
"""
    )

    uvicorn.run(app, host=host, port=port)
