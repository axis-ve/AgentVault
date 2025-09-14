import asyncio
import os
from dotenv import load_dotenv

from .core import ContextManager, logger
from .adapters.openai_adapter import OpenAIAdapter
from .adapters.web3_adapter import Web3Adapter
from .wallet import AgentWalletManager
from .strategies import dca_once as _dca_once
from .strategies import send_when_gas_below as _send_when_gas_below

load_dotenv()

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:  # Provide lightweight stubs so tests can import without MCP SDK
    class _ServerStub:
        def __init__(self, *_args, **_kwargs):
            pass
        def tool(self, func=None, **_kwargs):
            def _decorator(f):
                return f
            return _decorator if func is None else func
    class _StdioStub:
        def run_server(self, _server):
            raise RuntimeError("MCP SDK not installed: 'mcp' package missing")
    Server = _ServerStub  # type: ignore
    stdio_server = _StdioStub()  # type: ignore


server = Server("agentvault-mcp")

_context_mgr: ContextManager | None = None
_wallet_mgr: AgentWalletManager | None = None


@server.tool
async def spin_up_wallet(agent_id: str) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.spin_up_wallet(agent_id)


@server.tool
async def query_balance(agent_id: str) -> float:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.query_balance(agent_id)


@server.tool
async def execute_transfer(agent_id: str, to_address: str, amount_eth: float, confirmation_code: str | None = None, dry_run: bool = False) -> str | dict:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    # Dry-run path for safer UX
    if dry_run:
        return await _wallet_mgr.simulate_transfer(agent_id, to_address, amount_eth)
    # Enforce limit via WalletManager; pass optional confirmation
    # Note: limit is configured via env AGENTVAULT_MAX_TX_ETH/AGENTVAULT_TX_CONFIRM_CODE
    return await _wallet_mgr.execute_transfer(agent_id, to_address, amount_eth, confirmation_code)


@server.tool
async def generate_response(user_message: str) -> str:
    if _context_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _context_mgr.generate_response(user_message)


@server.tool
async def list_wallets() -> dict[str, str]:
    """List agent_id to address mappings (no secrets)."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.list_wallets()


@server.tool
async def export_wallet_keystore(agent_id: str, passphrase: str) -> str:
    """Export the agent's wallet as an encrypted V3 keystore JSON string.

    Safe for backup/restore. Use a strong passphrase.
    """
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.export_wallet_keystore(agent_id, passphrase)


@server.tool
async def export_wallet_private_key(agent_id: str, confirmation_code: str | None = None) -> str:
    """Export plaintext private key (hex). Strongly discouraged and gated.

    Requires env AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1 and a matching AGENTVAULT_EXPORT_CODE.
    Prefer export_wallet_keystore.
    """
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.export_wallet_private_key(agent_id, confirmation_code)


@server.tool
async def simulate_transfer(agent_id: str, to_address: str, amount_eth: float) -> dict:
    """Estimate gas/fees for a transfer without broadcasting."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.simulate_transfer(agent_id, to_address, amount_eth)


@server.tool
async def request_faucet_funds(agent_id: str, amount_eth: float | None = None) -> dict:
    """Request testnet faucet funds and wait for balance to increase."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.request_faucet_funds(agent_id, amount_eth)


# -------- Phase 1 strategy tools (stateless) --------


@server.tool
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


@server.tool
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


async def main() -> None:
    global _context_mgr, _wallet_mgr

    api_key = os.getenv("OPENAI_API_KEY")
    # Default to a public Sepolia endpoint to support zero-setup
    rpc_url = os.getenv("WEB3_RPC_URL") or "https://ethereum-sepolia.publicnode.com"
    encrypt_key = os.getenv("ENCRYPT_KEY")
    # Generate and persist a Fernet key if not provided
    if not encrypt_key:
        from cryptography.fernet import Fernet
        store_path = os.getenv("AGENTVAULT_STORE", "agentvault_store.json")
        import os as _os
        key_path = _os.path.splitext(store_path)[0] + ".key"
        if _os.path.exists(key_path):
            with open(key_path, "rb") as f:
                encrypt_key = f.read().decode()
        else:
            encrypt_key = Fernet.generate_key().decode()
            with open(key_path, "wb") as f:
                f.write(encrypt_key.encode())

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

    logger.info("AgentVault MCP server starting")
    # Use stdio_server context manager per MCP SDK
    try:
        async with stdio_server() as (read, write):  # type: ignore[operator]
            await server.run(read, write)
    except TypeError:
        # Fallback for older SDK variants exposing run_server(server)
        stdio_server.run_server(server)  # type: ignore[attr-defined]


def cli() -> None:
    asyncio.run(main())

# Optional: register prompts/resources if SDK supports them
if hasattr(server, "prompt"):
    @server.prompt  # type: ignore[attr-defined]
    async def wallet_status(agent_id: str) -> str:
        """Summarize wallet status for an agent."""
        if _wallet_mgr is None:
            return "Server not initialized"
        try:
            bal = await _wallet_mgr.query_balance(agent_id)
            state = _context_mgr.schema.state if _context_mgr else {}
            addr = state.get(f"{agent_id}_wallet", {}).get("address", "<none>")
            return f"Agent {agent_id}: address={addr}, balance={bal} ETH"
        except Exception as e:
            return f"Error fetching status for {agent_id}: {e}"

if hasattr(server, "resource"):
    @server.resource("agentvault/context")  # type: ignore[attr-defined]
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
