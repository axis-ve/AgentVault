from __future__ import annotations

import argparse
import asyncio
import os
from typing import Dict

from .core import ContextManager
from .adapters.web3_adapter import Web3Adapter
from .wallet import AgentWalletManager
from .strategies import (
    send_when_gas_below,
    dca_once,
    scheduled_send_once,
    micro_tip_equal,
    micro_tip_amounts,
)


def _init_managers() -> tuple[ContextManager, AgentWalletManager]:
    rpc_url = os.getenv("WEB3_RPC_URL") or "https://ethereum-sepolia.publicnode.com"
    encrypt_key = os.getenv("ENCRYPT_KEY")
    if not encrypt_key:
        from cryptography.fernet import Fernet

        store_path = os.getenv("AGENTVAULT_STORE", "agentvault_store.json")
        key_path = os.path.splitext(store_path)[0] + ".key"
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                encrypt_key = f.read().decode()
        else:
            encrypt_key = Fernet.generate_key().decode()
            with open(key_path, "wb") as f:
                f.write(encrypt_key.encode())
    ctx = ContextManager()
    w3 = Web3Adapter(rpc_url)
    mgr = AgentWalletManager(ctx, w3, encrypt_key)
    return ctx, mgr


async def _cmd_create_wallet(args):
    _, mgr = _init_managers()
    addr = await mgr.spin_up_wallet(args.agent_id)
    print(addr)


async def _cmd_list_wallets(args):
    _, mgr = _init_managers()
    mapping = await mgr.list_wallets()
    for aid, addr in mapping.items():
        print(f"{aid}: {addr}")


async def _cmd_balance(args):
    _, mgr = _init_managers()
    bal = await mgr.query_balance(args.agent_id)
    print(bal)


async def _cmd_simulate(args):
    _, mgr = _init_managers()
    sim = await mgr.simulate_transfer(args.agent_id, args.to, args.amount)
    print(sim)


async def _cmd_send(args):
    _, mgr = _init_managers()
    if args.dry_run:
        sim = await mgr.simulate_transfer(args.agent_id, args.to, args.amount)
        print(sim)
        return
    tx = await mgr.execute_transfer(
        args.agent_id, args.to, args.amount, args.confirmation_code
    )
    print(tx)


async def _cmd_faucet(args):
    _, mgr = _init_managers()
    res = await mgr.request_faucet_funds(args.agent_id, args.amount)
    print(res)


async def _cmd_export_keystore(args):
    _, mgr = _init_managers()
    ks = await mgr.export_wallet_keystore(args.agent_id, args.passphrase)
    print(ks)


async def _cmd_export_privkey(args):
    _, mgr = _init_managers()
    key = await mgr.export_wallet_private_key(args.agent_id, args.confirmation_code)
    print(key)


async def _cmd_strategy_send_when_gas_below(args):
    _, mgr = _init_managers()
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
    _, mgr = _init_managers()
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
    _, mgr = _init_managers()
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
    _, mgr = _init_managers()
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
    _, mgr = _init_managers()
    items = _parse_amounts(args.items)
    res = await micro_tip_amounts(
        mgr,
        args.agent_id,
        items,
        dry_run=args.dry_run,
        confirmation_code=args.confirmation_code,
    )
    print(res)


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

    args = p.parse_args()
    asyncio.run(args.func(args))

