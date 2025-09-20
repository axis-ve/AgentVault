import asyncio
import json
import os
from typing import Any, Callable
from dotenv import load_dotenv

from .core import ContextManager, logger
from .adapters.web3_adapter import Web3Adapter
from .wallet import AgentWalletManager
from .strategies import dca_once as _dca_once
from .strategies import send_when_gas_below as _send_when_gas_below
from .strategies import scheduled_send_once as _scheduled_send_once
from .strategies import micro_tip_equal as _micro_tip_equal
from .strategies import micro_tip_amounts as _micro_tip_amounts
from .strategy_manager import StrategyManager
from .ui import tipjar_page_html, dashboard_html
from .policy import PolicyConfig, PolicyEngine, run_with_policy, extract_agent_id

load_dotenv()

try:
    from mcp.server.fastmcp import FastMCP
    mcp_available = True
except ImportError:  # Provide lightweight stubs so tests can import without MCP SDK
    class _ServerStub:
        def __init__(self, *_args, **_kwargs):
            pass
        def tool(self, *args, **kwargs):
            """Tool decorator stub that works for both @server.tool() and @server.tool()"""
            def decorator(func):
                return func
            if len(args) == 1 and callable(args[0]):
                # Called as @server.tool() (without parentheses)
                return decorator(args[0])
            else:
                # Called as @server.tool() (with parentheses)
                return decorator
        def prompt(self, *args, **kwargs):
            def decorator(func):
                return func
            if len(args) == 1 and callable(args[0]):
                return decorator(args[0])
            else:
                return decorator
        def resource(self, *args, **kwargs):
            def decorator(func):
                return func
            if len(args) == 1 and callable(args[0]):
                return decorator(args[0])
            else:
                return decorator
        async def run_stdio_async(self):
            raise RuntimeError("MCP SDK not installed: 'mcp' package missing")
    FastMCP = _ServerStub  # type: ignore
    mcp_available = False


server = FastMCP("agentvault-mcp")

_context_mgr: ContextManager | None = None
_wallet_mgr: AgentWalletManager | None = None
_strategy_mgr: StrategyManager | None = None
_policy_engine: PolicyEngine | None = None


async def _policy_execute(
    tool_name: str,
    agent_id: str | None,
    request_payload: dict[str, Any] | None,
    coro_factory: Callable[[], Any],
) -> Any:
    if _policy_engine is None:
        return await coro_factory()
    return await run_with_policy(
        _policy_engine,
        tool_name=tool_name,
        agent_id=agent_id,
        request_payload=request_payload,
        call=coro_factory,
    )


def policy_guard(
    tool_name: str,
    *,
    agent_field: str | None = None,
    redact_fields: tuple[str, ...] = (),
):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            agent_id = None
            if agent_field:
                agent_id = kwargs.get(agent_field)
            else:
                agent_id = extract_agent_id(kwargs)
            request_payload = {k: v for k, v in kwargs.items() if k not in redact_fields}
            return await _policy_execute(tool_name, agent_id, request_payload, lambda: func(*args, **kwargs))

        return wrapper

    return decorator


# Tool functions will be registered in main() after initialization

@server.tool()
@policy_guard("spin_up_wallet", agent_field="agent_id")
async def spin_up_wallet(agent_id: str) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.spin_up_wallet(agent_id)


@server.tool()
@policy_guard("query_balance", agent_field="agent_id")
async def query_balance(agent_id: str) -> float:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.query_balance(agent_id)


@server.tool()
@policy_guard(
    "execute_transfer",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def execute_transfer(agent_id: str, to_address: str, amount_eth: float, confirmation_code: str | None = None, dry_run: bool = False) -> str | dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    # Dry-run path for safer UX
    if dry_run:
        return await _wallet_mgr.simulate_transfer(agent_id, to_address, amount_eth)
    # Enforce limit via WalletManager; pass optional confirmation
    # Note: limit is configured via env AGENTVAULT_MAX_TX_ETH/AGENTVAULT_TX_CONFIRM_CODE
    return await _wallet_mgr.execute_transfer(
        agent_id, to_address, amount_eth, confirmation_code
    )


@server.tool()
async def generate_response(user_message: str) -> str:
    if _context_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _context_mgr.generate_response(user_message)


@server.tool()
@policy_guard("list_wallets", agent_field=None)
async def list_wallets() -> dict[str, str]:
    """List agent_id to address mappings (no secrets)."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.list_wallets()


@server.tool()
@policy_guard("export_wallet_keystore", agent_field="agent_id", redact_fields=("passphrase",))
async def export_wallet_keystore(agent_id: str, passphrase: str) -> str:
    """Export the agent's wallet as an encrypted V3 keystore JSON string.

    Safe for backup/restore. Use a strong passphrase.
    """
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.export_wallet_keystore(agent_id, passphrase)


@server.tool()
async def generate_mnemonic(num_words: int = 12, language: str = "english") -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.generate_mnemonic(num_words=num_words, language=language)


@server.tool()
@policy_guard(
    "import_wallet_from_private_key",
    agent_field="agent_id",
    redact_fields=("private_key",),
)
async def import_wallet_from_private_key(
    agent_id: str, private_key: str, rotate: bool = False
) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.import_wallet_from_private_key(
        agent_id, private_key, rotate=rotate
    )


@server.tool()
@policy_guard(
    "import_wallet_from_mnemonic",
    agent_field="agent_id",
    redact_fields=("mnemonic", "passphrase"),
)
async def import_wallet_from_mnemonic(
    agent_id: str,
    mnemonic: str,
    path: str | None = None,
    passphrase: str | None = None,
    rotate: bool = False,
) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.import_wallet_from_mnemonic(
        agent_id,
        mnemonic,
        path=path,
        passphrase=passphrase,
        rotate=rotate,
    )


@server.tool()
@policy_guard(
    "import_wallet_from_encrypted_json",
    agent_field="agent_id",
    redact_fields=("encrypted_json", "password"),
)
async def import_wallet_from_encrypted_json(
    agent_id: str, encrypted_json: str, password: str, rotate: bool = False
) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.import_wallet_from_encrypted_json(
        agent_id, encrypted_json, password, rotate=rotate
    )


@server.tool()
@policy_guard("encrypt_wallet_keystore", agent_field="agent_id", redact_fields=("password",))
async def encrypt_wallet_keystore(agent_id: str, password: str) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.encrypt_wallet_json(agent_id, password)


@server.tool()
@policy_guard("decrypt_wallet_keystore", agent_field=None, redact_fields=("encrypted_json", "password"))
async def decrypt_wallet_keystore(encrypted_json: str, password: str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.decrypt_wallet_json(encrypted_json, password)


@server.tool()
@policy_guard(
    "export_wallet_private_key",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def export_wallet_private_key(agent_id: str, confirmation_code: str | None = None) -> str:
    """Export plaintext private key (hex). Strongly discouraged and gated.

    Requires env AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1 and a matching AGENTVAULT_EXPORT_CODE.
    Prefer export_wallet_keystore.
    """
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.export_wallet_private_key(agent_id, confirmation_code)


@server.tool()
@policy_guard("sign_message", agent_field="agent_id", redact_fields=("message",))
async def sign_message(agent_id: str, message: str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.sign_message(agent_id, message)


@server.tool()
async def verify_message(address: str, message: str, signature: str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.verify_message(address, message, signature)


@server.tool()
@policy_guard("sign_typed_data", agent_field="agent_id", redact_fields=("typed_data",))
async def sign_typed_data(agent_id: str, typed_data: dict | str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    payload = typed_data
    if isinstance(payload, str):
        payload = json.loads(payload)
    return await _wallet_mgr.sign_typed_data(agent_id, payload)


@server.tool()
async def verify_typed_data(address: str, typed_data: dict | str, signature: str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    payload = typed_data
    if isinstance(payload, str):
        payload = json.loads(payload)
    return await _wallet_mgr.verify_typed_data(address, payload, signature)


@server.tool()
@policy_guard(
    "simulate_transfer",
    agent_field="agent_id",
    redact_fields=(),
)
async def simulate_transfer(agent_id: str, to_address: str, amount_eth: float) -> dict:
    """Estimate gas/fees for a transfer without broadcasting."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.simulate_transfer(agent_id, to_address, amount_eth)


@server.tool()
@policy_guard(
    "request_faucet_funds",
    agent_field="agent_id",
)
async def request_faucet_funds(agent_id: str, amount_eth: float | None = None) -> dict:
    """Request testnet faucet funds and wait for balance to increase."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.request_faucet_funds(agent_id, amount_eth)


@server.tool()
@policy_guard("provider_status", agent_field=None)
async def provider_status() -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.provider_status()


@server.tool()
@policy_guard("inspect_contract", agent_field=None)
async def inspect_contract(address: str) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.inspect_contract(address)


# -------- Phase 1 strategy tools (stateless) --------


@server.tool()
@policy_guard(
    "send_when_gas_below",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def send_when_gas_below(
    agent_id: str,
    to_address: str,
    amount_eth: float,
    max_base_fee_gwei: float,
    dry_run: bool = False,
    confirmation_code: str | None = None,
) -> dict:
    """Send only when base fee per gas is below threshold.

    Returns a dict with action and either a tx_hash or a simulation.
    """
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _send_when_gas_below(
        _wallet_mgr,
        agent_id,
        to_address,
        amount_eth,
        max_base_fee_gwei,
        dry_run=dry_run,
        confirmation_code=confirmation_code,
    )


@server.tool()
@policy_guard(
    "dca_once",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def dca_once(
    agent_id: str,
    to_address: str,
    amount_eth: float,
    max_base_fee_gwei: float | None = None,
    dry_run: bool = False,
    confirmation_code: str | None = None,
) -> dict:
    """Perform a single DCA transfer if safe (simulate then send)."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _dca_once(
        _wallet_mgr,
        agent_id,
        to_address,
        amount_eth,
        max_base_fee_gwei=max_base_fee_gwei,
        dry_run=dry_run,
        confirmation_code=confirmation_code,
    )


@server.tool()
@policy_guard(
    "scheduled_send_once",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def scheduled_send_once(
    agent_id: str,
    to_address: str,
    amount_eth: float,
    send_at_iso: str,
    dry_run: bool = False,
    confirmation_code: str | None = None,
) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _scheduled_send_once(
        _wallet_mgr,
        agent_id,
        to_address,
        amount_eth,
        send_at_iso,
        dry_run=dry_run,
        confirmation_code=confirmation_code,
    )


@server.tool()
@policy_guard(
    "micro_tip_equal",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def micro_tip_equal(
    agent_id: str,
    recipients: list[str],
    total_amount_eth: float,
    dry_run: bool = False,
    confirmation_code: str | None = None,
) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _micro_tip_equal(
        _wallet_mgr,
        agent_id,
        recipients,
        total_amount_eth,
        dry_run=dry_run,
        confirmation_code=confirmation_code,
    )


@server.tool()
@policy_guard(
    "micro_tip_amounts",
    agent_field="agent_id",
    redact_fields=("confirmation_code",),
)
async def micro_tip_amounts(
    agent_id: str,
    items: dict[str, float],
    dry_run: bool = False,
    confirmation_code: str | None = None,
) -> dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _micro_tip_amounts(
        _wallet_mgr,
        agent_id,
        items,
        dry_run=dry_run,
        confirmation_code=confirmation_code,
    )


# -------- Phase 2 strategy lifecycle tools (stateful) --------


@server.tool()
@policy_guard("create_strategy_dca", agent_field="agent_id")
async def create_strategy_dca(
    label: str,
    agent_id: str,
    to_address: str,
    amount_eth: float,
    interval_seconds: int,
    max_base_fee_gwei: float | None = None,
    daily_cap_eth: float | None = None,
) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.create_strategy_dca(
        label,
        agent_id,
        to_address,
        amount_eth,
        interval_seconds,
        max_base_fee_gwei=max_base_fee_gwei,
        daily_cap_eth=daily_cap_eth,
    )


@server.tool()
@policy_guard("start_strategy", agent_field=None)
async def start_strategy(label: str) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.start_strategy(label)


@server.tool()
@policy_guard("stop_strategy", agent_field=None)
async def stop_strategy(label: str) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.stop_strategy(label)


@server.tool()
@policy_guard("strategy_status", agent_field=None)
async def strategy_status(label: str) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.strategy_status(label)


@server.tool()
@policy_guard("tick_strategy", agent_field=None, redact_fields=("confirmation_code",))
async def tick_strategy(
    label: str, dry_run: bool = False, confirmation_code: str | None = None
) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.tick_strategy(
        label, dry_run=dry_run, confirmation_code=confirmation_code
    )


@server.tool()
@policy_guard("list_strategies", agent_field="agent_id")
async def list_strategies(agent_id: str | None = None) -> dict:
    """List all strategies or those for a specific agent_id."""
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    if agent_id:
        return await _strategy_mgr.list_strategies_for_agent(agent_id)
    return await _strategy_mgr.list_strategies()


@server.tool()
@policy_guard("delete_strategy", agent_field=None)
async def delete_strategy(label: str) -> dict:
    if _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _strategy_mgr.delete_strategy(label)


# -------- UI helpers (HTML returned directly; no filesystem writes) --------


@server.tool()
@policy_guard("generate_tipjar_page", agent_field="agent_id")
async def generate_tipjar_page(agent_id: str, amount_eth: float | None = None) -> str:
    """Return a minimal tip jar HTML page for the agent's wallet."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    addr = await _wallet_mgr.spin_up_wallet(agent_id)
    return tipjar_page_html(addr, amount_eth)


@server.tool()
async def generate_dashboard_page() -> str:
    """Return a static HTML dashboard of known wallets and strategies."""
    if _wallet_mgr is None or _strategy_mgr is None:
        raise RuntimeError("Server not initialized")
    # Build wallet summaries with balances when possible
    wallets = []
    for aid, ws in _wallet_mgr.wallets.items():
        try:
            bal = await _wallet_mgr.query_balance(aid)
        except Exception:
            bal = "?"
        wallets.append({"agent_id": aid, "address": ws.address, "balance_eth": bal})
    strategies = await _strategy_mgr.list_strategies()
    return dashboard_html(wallets, strategies)


async def main() -> None:
    global _context_mgr, _wallet_mgr, _policy_engine

    api_key = os.getenv("OPENAI_API_KEY")
    # Default to a public Sepolia endpoint to support zero-setup; prefer explicit Alchemy config
    def _alchemy_http_default() -> str | None:
        key = os.getenv("ALCHEMY_API_KEY")
        if not key:
            return None
        network = os.getenv("ALCHEMY_NETWORK", "sepolia").strip()
        return f"https://eth-{network}.g.alchemy.com/v2/{key}"

    rpc_url = (
        os.getenv("WEB3_RPC_URL")
        or os.getenv("ALCHEMY_HTTP_URL")
        or _alchemy_http_default()
        or "https://ethereum-sepolia.publicnode.com"
    )
    encrypt_key = os.getenv("ENCRYPT_KEY")
    # Generate and persist a Fernet key if not provided; validate if provided
    from cryptography.fernet import Fernet as _Fernet
    store_path = os.getenv("AGENTVAULT_STORE", "agentvault_store.json")
    import os as _os
    key_path = _os.path.splitext(store_path)[0] + ".key"
    if not encrypt_key:
        if _os.path.exists(key_path):
            with open(key_path, "rb") as f:
                encrypt_key = f.read().decode()
        else:
            encrypt_key = _Fernet.generate_key().decode()
            with open(key_path, "wb") as f:
                f.write(encrypt_key.encode())
            try:
                _os.chmod(key_path, 0o600)
            except Exception:
                pass
    else:
        try:
            _Fernet(encrypt_key.encode())
        except Exception:
            logger.warning(
                "Invalid ENCRYPT_KEY provided; falling back to sidecar or generated key"
            )
            if _os.path.exists(key_path):
                with open(key_path, "rb") as f:
                    encrypt_key = f.read().decode()
            else:
                encrypt_key = _Fernet.generate_key().decode()
                with open(key_path, "wb") as f:
                    f.write(encrypt_key.encode())
                try:
                    _os.chmod(key_path, 0o600)
                except Exception:
                    pass

    _context_mgr = ContextManager(max_tokens=int(os.getenv("MCP_MAX_TOKENS", 4096)))
    # Register LLM adapter (OpenAI, Ollama, or a null fallback)
    if api_key:
        from .adapters.openai_adapter import OpenAIAdapter as _OpenAIAdapter
        openai_adapter = _OpenAIAdapter(api_key)
        _context_mgr.register_adapter("openai", openai_adapter)
    else:
        try:
            from .adapters.ollama_adapter import OllamaAdapter as _Ollama
            _context_mgr.register_adapter("openai", _Ollama())
        except Exception:
            class _NullLLM:
                async def call(self, context):
                    return "LLM not configured; set OPENAI_API_KEY or run Ollama locally."
            _context_mgr.register_adapter("openai", _NullLLM())

    web3_adapter = Web3Adapter(rpc_url)
    _context_mgr.register_adapter("web3", web3_adapter)
    _wallet_mgr = AgentWalletManager(_context_mgr, web3_adapter, encrypt_key)
    _strategy_mgr = StrategyManager(_wallet_mgr)
    _policy_engine = PolicyEngine(_wallet_mgr.session_maker, PolicyConfig.load())

    logger.info("AgentVault MCP server starting")
    if not mcp_available:
        raise RuntimeError("MCP SDK not installed: 'mcp' package missing")

    # Use FastMCP stdio transport
    await server.run_stdio_async()


def cli() -> None:
    asyncio.run(main())

# Register prompts and resources using FastMCP API
@server.prompt()
async def wallet_status(agent_id: str) -> list:
    """Summarize wallet status for an agent."""
    if _wallet_mgr is None:
        content = "Server not initialized"
    else:
        try:
            bal = await _wallet_mgr.query_balance(agent_id)
            state = _context_mgr.schema.state if _context_mgr else {}
            addr = state.get(f"{agent_id}_wallet", {}).get("address", "<none>")
            content = f"Agent {agent_id}: address={addr}, balance={bal} ETH"
        except Exception as e:
            content = f"Error fetching status for {agent_id}: {e}"

    return [{"role": "user", "content": {"type": "text", "text": content}}]

@server.resource("agentvault://context")
async def agentvault_context() -> str:
    """Expose a sanitized snapshot of context state."""
    if _context_mgr is None:
        return "{}"
    s = _context_mgr.schema.model_dump()
    state = s.get("state", {})
    safe_state = {k: v for k, v in state.items() if not (k.endswith("_wallet") or k.endswith("_balance"))}
    s["state"] = safe_state
    import json as _json
    return _json.dumps(s)
