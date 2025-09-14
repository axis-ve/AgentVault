import asyncio
import os
from dotenv import load_dotenv

from .core import ContextManager, logger
from .adapters.openai_adapter import OpenAIAdapter
from .adapters.web3_adapter import Web3Adapter
from .wallet import AgentWalletManager

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
async def execute_transfer(agent_id: str, to_address: str, amount_eth: float) -> str:
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.execute_transfer(agent_id, to_address, amount_eth)


@server.tool
async def generate_response(user_message: str) -> str:
    if _context_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _context_mgr.generate_response(user_message)


async def main() -> None:
    global _context_mgr, _wallet_mgr

    api_key = os.getenv("OPENAI_API_KEY")
    rpc_url = os.getenv("WEB3_RPC_URL")
    encrypt_key = os.getenv("ENCRYPT_KEY")
    if not all([api_key, rpc_url, encrypt_key]):
        raise ValueError("Missing env vars—check .env")

    _context_mgr = ContextManager(max_tokens=int(os.getenv("MCP_MAX_TOKENS", 4096)))
    openai_adapter = OpenAIAdapter(api_key)
    web3_adapter = Web3Adapter(rpc_url)
    _context_mgr.register_adapter("openai", openai_adapter)
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
