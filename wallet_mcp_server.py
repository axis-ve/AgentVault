import asyncio
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Literal

import structlog
import tiktoken
from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, field_validator
from web3 import AsyncWeb3
from web3.exceptions import InvalidTransaction

from dotenv import load_dotenv
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


# Load env
load_dotenv()

# Configure stdlib logging level from env before structlog setup
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))


# Structured logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("mcp")


class MCPError(Exception):
    """Base exception for MCP operations."""
    pass


class ContextOverflowError(MCPError):
    """Raised when context exceeds token limits after trimming."""
    pass


class WalletError(MCPError):
    """Raised for wallet-specific issues."""
    pass


class ContextSchema(BaseModel):
    """MCP Protocol Schema: Validates and structures context."""
    history: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation history."
    )
    system_prompt: str = Field(
        default="", description="System-level instructions."
    )
    state: Dict[str, Any] = Field(
        default_factory=dict, description="Persistent state (e.g., wallet info)."
    )
    # Context budget (approx) for prompt + history
    max_tokens: int = Field(default=4096, gt=0, description="Context token budget.")
    # Completion budget for the model's reply
    completion_max_tokens: int = Field(
        default=512, gt=0, description="Max tokens for model completion."
    )
    trim_strategy: Literal["recency", "semantic"] = Field(
        default="recency", description="Trimming method."
    )

    @field_validator("history")
    def validate_history(cls, v):
        for msg in v:
            if "role" not in msg or "content" not in msg:
                raise ValueError("History messages must have 'role' and 'content'.")
        return v


class WalletState(BaseModel):
    """Sub-schema for wallet persistence in context."""
    address: str
    encrypted_privkey: bytes
    chain_id: int = 11155111  # Sepolia testnet default
    last_nonce: Optional[int] = None


class AbstractAdapter(ABC):
    """Abstract base for external adapters (e.g., LLM, Blockchain)."""

    @abstractmethod
    async def call(self, context: ContextSchema) -> Any:
        pass


class OpenAIAdapter(AbstractAdapter):
    """Production adapter for OpenAI LLM calls."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def call(self, context: ContextSchema) -> str:
        messages = [{"role": "system", "content": context.system_prompt}] + context.history
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=context.completion_max_tokens,
                temperature=0.7,
            )
            reply = response.choices[0].message.content
            logger.info(
                "LLM call successful",
                tokens_used=response.usage.total_tokens if response.usage else 0,
            )
            return reply
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            raise MCPError(f"OpenAI API error: {e}")


class Web3Adapter(AbstractAdapter):
    """Production adapter for Ethereum interactions."""

    def __init__(self, rpc_url: str):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))

    async def ensure_connection(self) -> bool:
        if await self.w3.is_connected():
            logger.info("Web3 connected")
            return True
        raise WalletError("Failed to connect to RPC")

    async def get_nonce(self, address: str) -> int:
        nonce = await self.w3.eth.get_transaction_count(address)
        logger.debug("Nonce fetched", address=address, nonce=nonce)
        return nonce


class ContextManager:
    """Core MCP: Manages context with trimming and state injection."""

    def __init__(
        self,
        max_tokens: int = 4096,
        trim_strategy: str = "recency",
        encoding_name: str = "o200k_base",  # Recommended for GPT-4o
        logger: structlog.stdlib.BoundLogger = logger,
    ):
        self.schema = ContextSchema(max_tokens=max_tokens, trim_strategy=trim_strategy)
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.logger = logger.bind(component="ContextManager")
        self.adapters: Dict[str, AbstractAdapter] = {}

    def register_adapter(self, name: str, adapter: AbstractAdapter):
        """Dependency injection for adapters."""
        self.adapters[name] = adapter
        self.logger.info("Adapter registered", name=name)

    async def append_to_history(self, role: str, content: str) -> None:
        """Append message and trim if needed."""
        self.schema.history.append({"role": role, "content": content})
        await self._trim_context()

    async def _trim_context(self) -> None:
        """Apply trimming strategy atomically."""
        token_count = self._calculate_tokens()
        if token_count > self.schema.max_tokens * 0.9:  # Proactive trim
            if self.schema.trim_strategy == "recency":
                while (
                    token_count > self.schema.max_tokens * 0.8
                    and len(self.schema.history) > 1
                ):
                    removed = self.schema.history.pop(0)
                    token_count = self._calculate_tokens()
                    self.logger.debug("Trimmed message", removed=removed["role"])
            else:  # Semantic: Placeholder for embeddings (implement with sentence-transformers in extension)
                if not getattr(self, "_semantic_trim_warned", False):
                    self.logger.warning(
                        "Semantic trim requested but not implemented in base"
                    )
                    self._semantic_trim_warned = True
                # For production, integrate FAISS here with pre-computed embeddings
            if self._calculate_tokens() > self.schema.max_tokens:
                raise ContextOverflowError(
                    f"Context overflow after trim: {self._calculate_tokens()} tokens"
                )

    def _calculate_tokens(self) -> int:
        sys_tokens = len(self.encoding.encode(self.schema.system_prompt))
        hist_tokens = sum(
            len(self.encoding.encode(msg["content"])) for msg in self.schema.history
        )
        return sys_tokens + hist_tokens + len(self.schema.state) * 10  # Rough state overhead

    async def generate_response(
        self, user_message: str, adapter_name: str = "openai"
    ) -> str:
        """Full cycle: Append, call adapter, append response."""
        if adapter_name not in self.adapters:
            raise MCPError(f"Adapter {adapter_name} not registered")

        await self.append_to_history("user", user_message)
        adapter = self.adapters[adapter_name]
        reply = await adapter.call(self.schema)
        await self.append_to_history("assistant", reply)
        self.logger.info("Response generated", tokens=self._calculate_tokens())
        return reply

    def update_state(self, key: str, value: Any) -> None:
        """Inject state (e.g., wallet info) into schema."""
        self.schema.state[key] = value
        self.logger.debug("State updated", key=key)


class AgentWalletManager:
    """Wallet-specific MCP layer: Secure, async wallet ops with context integration."""

    def __init__(
        self,
        context_manager: ContextManager,
        web3_adapter: Web3Adapter,
        encrypt_key: str,
        logger: structlog.stdlib.BoundLogger = logger,
    ):
        self.context = context_manager
        self.web3 = web3_adapter
        self.encryptor = Fernet(encrypt_key.encode())
        self.logger = logger.bind(component="AgentWalletManager")
        self.wallets: Dict[str, WalletState] = {}  # agent_id -> WalletState

    async def spin_up_wallet(self, agent_id: str) -> str:
        """Generate and persist HD wallet for agent."""
        await self.web3.ensure_connection()
        account = Account.create()
        # Encrypt raw key bytes for storage
        encrypted_privkey = self.encryptor.encrypt(bytes(account.key))
        # Async chain_id in AsyncWeb3 6.x
        chain_id_value = await self.web3.w3.eth.chain_id
        wallet_state = WalletState(
            address=account.address,
            encrypted_privkey=encrypted_privkey,
            chain_id=chain_id_value,
        )
        self.wallets[agent_id] = wallet_state
        self.context.update_state(
            f"{agent_id}_wallet", wallet_state.dict(exclude={"encrypted_privkey"})
        )
        await self.context.append_to_history(
            "system", f"Wallet created for {agent_id}: {account.address}"
        )
        self.logger.info("Wallet spun up", agent_id=agent_id, address=account.address)
        return account.address

    async def query_balance(self, agent_id: str) -> float:
        """Fetch and cache balance, inject into context."""
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}—spin up first.")

        wallet = self.wallets[agent_id]
        await self.web3.ensure_connection()
        balance_wei = await self.web3.w3.eth.get_balance(wallet.address)
        balance_eth = self.web3.w3.from_wei(balance_wei, "ether")

        self.context.update_state(f"{agent_id}_balance", float(balance_eth))
        await self.context.append_to_history(
            "system", f"Balance for {agent_id}: {balance_eth} ETH"
        )
        self.logger.info("Balance queried", agent_id=agent_id, balance=balance_eth)
        return float(balance_eth)

    async def execute_transfer(
        self, agent_id: str, to_address: str, amount_eth: float
    ) -> str:
        """Sign and send transfer, update context with txn details."""
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")

        wallet = self.wallets[agent_id]
        try:
            privkey_bytes = self.encryptor.decrypt(wallet.encrypted_privkey)
            account = Account.from_key(privkey_bytes)

            if account.address != wallet.address:
                raise WalletError("Key mismatch—security breach.")

            # Basic validation
            if amount_eth <= 0:
                raise WalletError("Amount must be positive.")
            if not self.web3.w3.is_address(to_address):
                raise WalletError("Invalid recipient address.")

            nonce = await self.web3.get_nonce(wallet.address)
            # Prefer EIP-1559 fields
            priority_fee = await self.web3.w3.eth.max_priority_fee
            latest_block = await self.web3.w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas") or 0
            max_fee = base_fee + priority_fee * 2

            txn = {
                "to": to_address,
                "value": self.web3.w3.to_wei(amount_eth, "ether"),
                "nonce": nonce,
                "chainId": wallet.chain_id,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "type": 2,
            }
            # Estimate gas to reduce failure
            gas_estimate = await self.web3.w3.eth.estimate_gas({**txn, "from": wallet.address})
            txn["gas"] = gas_estimate

            signed_txn = self.web3.w3.eth.account.sign_transaction(txn, privkey_bytes)
            tx_hash = await self.web3.w3.eth.send_raw_transaction(
                signed_txn.rawTransaction
            )

            # Update nonce for next txn
            wallet.last_nonce = nonce + 1

            receipt = await self.web3.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120
            )
            if receipt.status != 1:
                raise WalletError("Transaction failed on-chain.")

            await self.context.append_to_history(
                "system",
                f"Transfer executed for {agent_id}: {amount_eth} ETH to {to_address}. Hash: {tx_hash.hex()}",
            )
            self.logger.info(
                "Transfer successful",
                agent_id=agent_id,
                tx_hash=tx_hash.hex(),
                amount=amount_eth,
            )
            return tx_hash.hex()

        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except InvalidTransaction as e:
            self.logger.error("Invalid txn", error=str(e), agent_id=agent_id)
            raise WalletError(f"Transaction invalid: {e}")
        except Exception as e:
            self.logger.error("Transfer failed", error=str(e), agent_id=agent_id)
            raise WalletError(f"Transfer error: {e}")


# Global server and late-bound managers
server = Server("wallet-mcp")
_context_mgr: Optional[ContextManager] = None
_wallet_mgr: Optional[AgentWalletManager] = None


@server.tool
async def spin_up_wallet(agent_id: str) -> str:
    """Generate and persist a new HD wallet for the specified agent."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.spin_up_wallet(agent_id)


@server.tool
async def query_balance(agent_id: str) -> float:
    """Query the current ETH balance for the agent's wallet."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.query_balance(agent_id)


@server.tool
async def execute_transfer(agent_id: str, to_address: str, amount_eth: float) -> str:
    """Execute an ETH transfer from the agent's wallet to the specified address."""
    if _wallet_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _wallet_mgr.execute_transfer(agent_id, to_address, amount_eth)


@server.tool
async def generate_response(user_message: str) -> str:
    """Generate a context-aware response using the LLM."""
    if _context_mgr is None:
        raise RuntimeError("Server not initialized")
    return await _context_mgr.generate_response(user_message)


async def main() -> None:
    """Initialize managers and run the MCP stdio server."""
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

    stdio_server.run_server(server)


def cli() -> None:
    """CLI entry point for running the MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    cli()
