from __future__ import annotations

import argparse
import asyncio
import os
from typing import Dict

import uvicorn

from .core import ContextManager, logger
from .adapters.web3_adapter import Web3Adapter
from .wallet import AgentWalletManager
from .policy import PolicyConfig, PolicyEngine
from .db.repositories import EventRepository
from .admin_api import create_app
from .strategies import (
    send_when_gas_below,
    dca_once,
    scheduled_send_once,
    micro_tip_equal,
    micro_tip_amounts,
)
from .tipjar import generate_tipjar_qr
from .strategy_manager import StrategyManager
from .ui import write_tipjar_page, write_dashboard_page


def _resolve_alchemy_http_default() -> str | None:
    key = os.getenv("ALCHEMY_API_KEY")
    if not key:
        return None
    network = os.getenv("ALCHEMY_NETWORK", "sepolia").strip()
    # Default to Ethereum Sepolia family; user can override fully via ALCHEMY_HTTP_URL
    return f"https://eth-{network}.g.alchemy.com/v2/{key}"


def _init_managers() -> tuple[ContextManager, AgentWalletManager, PolicyEngine]:
    rpc_url = os.getenv("WEB3_RPC_URL") or os.getenv("ALCHEMY_HTTP_URL") or _resolve_alchemy_http_default() or "https://ethereum-sepolia.publicnode.com"
    encrypt_key = os.getenv("ENCRYPT_KEY")
    from cryptography.fernet import Fernet
    store_path = os.getenv("AGENTVAULT_STORE", "agentvault_store.json")
    key_path = os.path.splitext(store_path)[0] + ".key"
    if not encrypt_key:
        # Auto-generate or reuse sidecar key
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                encrypt_key = f.read().decode()
        else:
            encrypt_key = Fernet.generate_key().decode()
            with open(key_path, "wb") as f:
                f.write(encrypt_key.encode())
            try:
                os.chmod(key_path, 0o600)
            except Exception:
                pass
    else:
        # Validate provided key; if invalid, fall back to sidecar or generate
        try:
            Fernet(encrypt_key.encode())
        except Exception:
            logger.warning(
                "Invalid ENCRYPT_KEY provided; falling back to sidecar or generated key"
            )
            if os.path.exists(key_path):
                with open(key_path, "rb") as f:
                    encrypt_key = f.read().decode()
            else:
                encrypt_key = Fernet.generate_key().decode()
                with open(key_path, "wb") as f:
                    f.write(encrypt_key.encode())
                try:
                    os.chmod(key_path, 0o600)
                except Exception:
                    pass
    ctx = ContextManager()
    w3 = Web3Adapter(rpc_url)
    mgr = AgentWalletManager(ctx, w3, encrypt_key)
    policy_engine = PolicyEngine(mgr.session_maker, PolicyConfig.load())
    return ctx, mgr, policy_engine


async def _cmd_create_wallet(args):
    _, mgr, _ = _init_managers()
    addr = await mgr.spin_up_wallet(args.agent_id)
    print(addr)


async def _cmd_list_wallets(args):
    _, mgr, _ = _init_managers()
    mapping = await mgr.list_wallets()
    for aid, addr in mapping.items():
        print(f"{aid}: {addr}")


async def _cmd_balance(args):
    _, mgr, _ = _init_managers()
    bal = await mgr.query_balance(args.agent_id)
    print(bal)


async def _cmd_simulate(args):
    _, mgr, _ = _init_managers()
    sim = await mgr.simulate_transfer(args.agent_id, args.to, args.amount)
    print(sim)


async def _cmd_send(args):
    _, mgr, _ = _init_managers()
    if args.dry_run:
        sim = await mgr.simulate_transfer(args.agent_id, args.to, args.amount)
        print(sim)
        return
    tx = await mgr.execute_transfer(
        args.agent_id, args.to, args.amount, args.confirmation_code
    )
    print(tx)


async def _cmd_faucet(args):
    _, mgr, _ = _init_managers()
    res = await mgr.request_faucet_funds(args.agent_id, args.amount)
    print(res)


async def _cmd_export_keystore(args):
    _, mgr, _ = _init_managers()
    ks = await mgr.export_wallet_keystore(args.agent_id, args.passphrase)
    print(ks)


async def _cmd_export_privkey(args):
    _, mgr, _ = _init_managers()
    key = await mgr.export_wallet_private_key(args.agent_id, args.confirmation_code)
    print(key)


async def _cmd_strategy_send_when_gas_below(args):
    _, mgr, _ = _init_managers()
    res = await send_when_gas_below(
        mgr,
        args.agent_id,
        args.to,
        args.amount,
        args.max_base_fee_gwei,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


async def _cmd_strategy_dca_once(args):
    _, mgr, _ = _init_managers()
    res = await dca_once(
        mgr,
        args.agent_id,
        args.to,
        args.amount,
        max_base_fee_gwei=args.max_base_fee_gwei,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


async def _cmd_strategy_scheduled_once(args):
    _, mgr, _ = _init_managers()
    res = await scheduled_send_once(
        mgr,
        args.agent_id,
        args.to,
        args.amount,
        args.at,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


async def _cmd_strategy_micro_equal(args):
    _, mgr, _ = _init_managers()
    recipients = [x for x in args.recipients.split(",") if x]
    res = await micro_tip_equal(
        mgr,
        args.agent_id,
        recipients,
        args.total_amount,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


def _parse_amounts(text: str) -> Dict[str, float]:
    items: Dict[str, float] = {}
    for pair in text.split(","):
        if not pair:
            continue
        addr, _, amt = pair.partition("=")
        if not addr or not amt:
            raise ValueError("items must be addr=amount,addr=amount,...")
        items[addr] = float(amt)
    return items


async def _cmd_strategy_micro_amounts(args):
    _, mgr, _ = _init_managers()
    items = _parse_amounts(args.items)
    res = await micro_tip_amounts(
        mgr,
        args.agent_id,
        items,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


async def _cmd_tipjar(args):
    _, mgr, _ = _init_managers()
    addr = await mgr.spin_up_wallet(args.agent_id)
    out = args.out or f"tipjar-{args.agent_id}.png"
    path = generate_tipjar_qr(addr, out, args.amount)
    print({"address": addr, "qr": path})


async def _cmd_tipjar_page(args):
    _, mgr, _ = _init_managers()
    addr = await mgr.spin_up_wallet(args.agent_id)
    out = args.out or f"tipjar-{args.agent_id}.html"
    path = write_tipjar_page(out, addr, args.amount)
    print({"address": addr, "page": path})


async def _cmd_dashboard(args):
    _, mgr, policy_engine = _init_managers()
    sm = StrategyManager(mgr)
    wallets = []
    wallet_map = await mgr.list_wallets()
    for aid, address in wallet_map.items():
        try:
            bal = await mgr.query_balance(aid)
        except Exception:
            bal = "?"
        wallets.append({"agent_id": aid, "address": address, "balance_eth": bal})
    out = args.out or "agentvault-dashboard.html"
    strategies = await sm.list_strategies()
    async with policy_engine.session_maker() as session:
        repo = EventRepository(session)
        events = [
            {
                "tool_name": rec.tool_name,
                "agent_id": rec.agent_id,
                "status": rec.status,
                "occurred_at": rec.occurred_at.isoformat() if rec.occurred_at else "",
            }
            for rec in await repo.list_events(50)
        ]
    path = write_dashboard_page(out, wallets, strategies, events)
    print({"page": path})


async def _cmd_provider_status(args):
    _, mgr, _ = _init_managers()
    info = await mgr.provider_status()
    print(info)


async def _cmd_inspect_contract(args):
    _, mgr, _ = _init_managers()
    details = await mgr.inspect_contract(args.address)
    print(details)


async def _cmd_admin_api(args):
    _, mgr, policy_engine = _init_managers()
    sm = StrategyManager(mgr)
    app = create_app(policy_engine)

    config = uvicorn.Config(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
    )
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:  # pragma: no cover
    p = argparse.ArgumentParser(prog="agentvault", description="AgentVault CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("create-wallet")
    s.add_argument("agent_id")
    s.set_defaults(func=_cmd_create_wallet)

    s = sub.add_parser("list-wallets")
    s.set_defaults(func=_cmd_list_wallets)

    s = sub.add_parser("balance")
    s.add_argument("agent_id")
    s.set_defaults(func=_cmd_balance)

    s = sub.add_parser("simulate")
    s.add_argument("agent_id")
    s.add_argument("to")
    s.add_argument("amount", type=float)
    s.set_defaults(func=_cmd_simulate)

    s = sub.add_parser("send")
    s.add_argument("agent_id")
    s.add_argument("to")
    s.add_argument("amount", type=float)
    s.add_argument("--confirmation-code")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=_cmd_send)

    s = sub.add_parser("faucet")
    s.add_argument("agent_id")
    s.add_argument("--amount", type=float)
    s.set_defaults(func=_cmd_faucet)

    s = sub.add_parser("export-keystore")
    s.add_argument("agent_id")
    s.add_argument("passphrase")
    s.set_defaults(func=_cmd_export_keystore)

    s = sub.add_parser("export-privkey")
    s.add_argument("agent_id")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_export_privkey)

    # Strategies
    strat = sub.add_parser("strategy")
    ssub = strat.add_subparsers(dest="s_cmd", required=True)

    s = ssub.add_parser("send-when-gas-below")
    s.add_argument("agent_id")
    s.add_argument("to")
    s.add_argument("amount", type=float)
    s.add_argument("max_base_fee_gwei", type=float)
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_strategy_send_when_gas_below)

    s = ssub.add_parser("dca-once")
    s.add_argument("agent_id")
    s.add_argument("to")
    s.add_argument("amount", type=float)
    s.add_argument("--max-base-fee-gwei", type=float)
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_strategy_dca_once)

    s = ssub.add_parser("scheduled-send-once")
    s.add_argument("agent_id")
    s.add_argument("to")
    s.add_argument("amount", type=float)
    s.add_argument("at", help="ISO8601 timestamp")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_strategy_scheduled_once)

    s = ssub.add_parser("micro-tip-equal")
    s.add_argument("agent_id")
    s.add_argument("recipients", help="comma-separated addresses")
    s.add_argument("total_amount", type=float)
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_strategy_micro_equal)

    s = ssub.add_parser("micro-tip-amounts")
    s.add_argument("agent_id")
    s.add_argument(
        "items",
        help="addr=amount,addr=amount (ETH amounts)",
    )
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--confirmation-code")
    s.set_defaults(func=_cmd_strategy_micro_amounts)

    s = sub.add_parser("tip-jar")
    s.add_argument("agent_id")
    s.add_argument("--amount", type=float)
    s.add_argument("--out")
    s.set_defaults(func=_cmd_tipjar)

    s = sub.add_parser("tip-jar-page")
    s.add_argument("agent_id")
    s.add_argument("--amount", type=float)
    s.add_argument("--out")
    s.set_defaults(func=_cmd_tipjar_page)

    s = sub.add_parser("dashboard")
    s.add_argument("--out")
    s.set_defaults(func=_cmd_dashboard)

    s = sub.add_parser("provider-info")
    s.set_defaults(func=_cmd_provider_status)

    s = sub.add_parser("inspect-contract")
    s.add_argument("address")
    s.set_defaults(func=_cmd_inspect_contract)

    api = sub.add_parser("admin-api")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=9900)
    api.add_argument("--log-level", default="info")
    api.add_argument("--reload", action="store_true")
    api.set_defaults(func=_cmd_admin_api)

    args = p.parse_args()
    asyncio.run(args.func(args))
