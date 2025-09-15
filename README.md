# AgentVault MCP

[![PyPI](https://img.shields.io/pypi/v/agentvault-mcp.svg)](https://pypi.org/project/agentvault-mcp/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](#)

  Secure context and wallet tools for autonomous AI agents, built on the Model Context Protocol (MCP). Exposes stdio MCP tools for Ethereum wallet management and a context-aware LLM, with structured logging and safe context trimming.

  ## Features
- ContextManager with proactive trimming and token counting (tiktoken)
  - If `tiktoken` is not installed, a heuristic fallback is used.
  - OpenAI adapter (async, configurable model)
  - Web3 wallet ops with EIP‑1559 fees and gas estimation
  - Fernet encryption of private keys; never persisted in plain text
  - MCP stdio server registering wallet + LLM tools

  ## Quickstart
  Zero‑setup (testnet):
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt && pip install -e .
  # No env needed: defaults to Sepolia public RPC and will auto-generate ENCRYPT_KEY sidecar
  python -m agentvault_mcp.server  # or: agentvault-mcp
  ```

  Pro config (custom RPC / OpenAI):
  ```bash
  export WEB3_RPC_URL=https://sepolia.infura.io/v3/...
  export OPENAI_API_KEY=sk-...
  export ENCRYPT_KEY=$(python -c "from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())")
  python -m agentvault_mcp.server
  ```

  ## Order of Operations (End‑to‑End)
  1) Start the MCP server
    - `python -m agentvault_mcp.server` (stdio MCP)
    - Purpose: launches the stdio server exposing wallet + LLM tools for MCP clients.
  2) Create a wallet for your agent
    - Tool: `spin_up_wallet(agent_id)` → returns `address`
    - Purpose: generates a unique ETH wallet, encrypts its key, persists it.
  3) Fund the wallet (testnet)
    - Tool: `request_faucet_funds(agent_id)` (requires `AGENTVAULT_FAUCET_URL`)
    - Or fund manually; then run `query_balance(agent_id)`.
    - Purpose: ensure there are funds for gas and transfers.
  4) Dry‑run a transfer (recommended)
    - Tool: `simulate_transfer(agent_id, to_address, amount_eth)`
    - Or call `execute_transfer(..., dry_run=True)`
    - Purpose: see gas, fee, and total cost; detect insufficient funds early.
  5) Execute a transfer (with optional limit gate)
    - Tool: `execute_transfer(agent_id, to_address, amount_eth, confirmation_code?)`
    - Purpose: signs and sends a real EIP‑1559 transaction. If
      `AGENTVAULT_MAX_TX_ETH` is set and the amount exceeds it, you must supply
      `confirmation_code` matching `AGENTVAULT_TX_CONFIRM_CODE`.
  6) Use the LLM
    - Tool: `generate_response(user_message)`
    - Purpose: produces a context‑aware reply via OpenAI (if configured) or
      local Ollama fallback.
  7) Export/backup (optional)
    - Tool: `export_wallet_keystore(agent_id, passphrase)` → V3 keystore JSON
    - Tool: `export_wallet_private_key(agent_id, confirmation_code?)` (gated)
    - Purpose: backup/portability; prefer keystore export.
  8) Manage/inspect
    - Tool: `list_wallets()` → `{agent_id: address}`
    - Optional prompt/resource (if supported): `wallet_status(agent_id)`,
      `agentvault/context`.

  ### MCP Client Example (Claude Desktop)
  ```json
  {
    "mcpServers": {
      "agentvault": {
        "command": "python",
        "args": ["-m", "agentvault_mcp.server"],
        "env": {
          "OPENAI_API_KEY": "...",
          "ENCRYPT_KEY": "...",
          "WEB3_RPC_URL": "..."
        }
      }
    }
  }
  ```

  ## Developer Integration

  You can use AgentVault MCP in two ways:

  - Via MCP clients (e.g., Claude Desktop) calling stdio tools.
  - Direct Python API for programmatic, sequential workflows.
  - CLI: `agentvault` for quick local control without MCP client.

  ### Direct Python API (Puppeteer‑style Orchestration)
  Use the wallet and adapters directly for end‑to‑end flows (create → fund →
  simulate → send):

  ```python
  import asyncio, os
  from agentvault_mcp.core import ContextManager
  from agentvault_mcp.adapters.web3_adapter import Web3Adapter
  from agentvault_mcp.wallet import AgentWalletManager

  async def flow():
      rpc = os.getenv("WEB3_RPC_URL") or "https://ethereum-sepolia.publicnode.com"
      key = os.getenv("ENCRYPT_KEY") or __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode()
      ctx = ContextManager(); w3 = Web3Adapter(rpc)
      mgr = AgentWalletManager(ctx, w3, key)
      agent = "trader"
      addr = await mgr.spin_up_wallet(agent)
      print("wallet:", addr)
      if os.getenv("AGENTVAULT_FAUCET_URL"):
          print(await mgr.request_faucet_funds(agent))
      print("balance:", await mgr.query_balance(agent))
      print("simulate:", await mgr.simulate_transfer(agent, "0x"+"1"*40, 0.001))
      # To send:
      # await mgr.execute_transfer(agent, "0x"+"1"*40, 0.001)

  asyncio.run(flow())
  ```

  - A runnable example is provided: `python examples/orchestrator.py`.
  - For “sequential thinking” workflows, compose these calls with your own
    decision logic (e.g., DCA, thresholds, rebalancing) before calling
    `execute_transfer`.

  ### CLI Commands
  Install the package and run:

  ```bash
  agentvault create-wallet <agent_id>
  agentvault list-wallets
  agentvault balance <agent_id>
  agentvault simulate <agent_id> <to> <amount>
  agentvault send <agent_id> <to> <amount> [--dry-run] [--confirmation-code CODE]
  agentvault faucet <agent_id> [--amount AMT]
  agentvault export-keystore <agent_id> <passphrase>
  agentvault export-privkey <agent_id> --confirmation-code CODE

  # Strategies (stateless)
  agentvault strategy send-when-gas-below <agent> <to> <amount> <max_gwei> [--dry-run]
  agentvault strategy dca-once <agent> <to> <amount> [--max-base-fee-gwei G] [--dry-run]
  agentvault strategy scheduled-send-once <agent> <to> <amount> <ISO8601> [--dry-run]
  agentvault strategy micro-tip-equal <agent> <addr1,addr2,...> <total_amount> [--dry-run]
  agentvault strategy micro-tip-amounts <agent> "addr1=0.01,addr2=0.02" [--dry-run]
  ```

  ## Tools
  - `spin_up_wallet(agent_id: str) -> str`
  - `query_balance(agent_id: str) -> float`
  - `execute_transfer(agent_id: str, to_address: str, amount_eth: float, confirmation_code?: str, dry_run?: bool) -> str | dict`
  - `generate_response(user_message: str) -> str`
  - `list_wallets() -> {agent_id: address}`
  - `export_wallet_keystore(agent_id: str, passphrase: str) -> str` (encrypted JSON)
  - `export_wallet_private_key(agent_id: str, confirmation_code?: str) -> str` (gated; discouraged)
  - `simulate_transfer(agent_id: str, to_address: str, amount_eth: float) -> dict`
  - `request_faucet_funds(agent_id: str, amount_eth?: float) -> {ok, start_balance, end_balance}`
  - `send_when_gas_below(agent_id: str, to_address: str, amount_eth: float, max_base_fee_gwei: float, dry_run?: bool, confirmation_code?: str) -> {action, ...}`
  - `dca_once(agent_id: str, to_address: str, amount_eth: float, max_base_fee_gwei?: float, dry_run?: bool, confirmation_code?: str) -> {action, ...}`
    
  ### Phase 2 (Stateful Lifecycle)
  - `create_strategy_dca(label: str, agent_id: str, to_address: str, amount_eth: float, interval_seconds: int, max_base_fee_gwei?: float, daily_cap_eth?: float) -> strategy`
  - `start_strategy(label: str) -> strategy`
  - `stop_strategy(label: str) -> strategy`
  - `strategy_status(label: str) -> strategy`
  - `tick_strategy(label: str, dry_run?: bool, confirmation_code?: str) -> {action, ...}`
    - Persisted state in `AGENTVAULT_STRATEGY_STORE`; `tick_strategy` performs
      simulate → limit checks → (optional) execute; schedules next run.
  - `list_strategies(agent_id?: str) -> {label: strategy}`
  - `delete_strategy(label: str) -> {deleted, strategy}`
  - `request_faucet_funds(agent_id: str, amount_eth?: float) -> {ok, start_balance, end_balance}`

  ## Optional MCP Features
  - A `wallet_status` prompt is registered when the SDK supports prompts.
  - An `agentvault/context` resource is registered when resources are supported; it returns a sanitized JSON snapshot of state.

  ## Security Notes
  - Private keys are encrypted with a Fernet key provided via `ENCRYPT_KEY`.
  - If `ENCRYPT_KEY` is not set, a Fernet key is auto-generated and stored beside `AGENTVAULT_STORE` (e.g., `agentvault_store.key`). Keep this file safe to restore wallets.
  - Only public wallet info is injected into context; resource output is sanitized.
  - Keystore export is preferred for backups; plaintext export is gated behind envs `AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1` and `AGENTVAULT_EXPORT_CODE`.
  - Wallet generation uses cryptographic randomness; addresses are checked for in-process uniqueness to prevent reuse.
  - Transfers above `AGENTVAULT_MAX_TX_ETH` require a matching `AGENTVAULT_TX_CONFIRM_CODE` passed via the `confirmation_code` argument.
  - Wallets persist to `AGENTVAULT_STORE` so they survive restarts (encrypted at rest).

  ## Repository Structure (What Each File Does)
  - `src/agentvault_mcp/__init__.py`
    - Defines core exceptions: `MCPError`, `ContextOverflowError`, `WalletError`.
  - `src/agentvault_mcp/core.py`
    - ContextSchema + ContextManager: history/state handling, token counting,
      proactive trimming, tiktoken fallback, structured logging setup.
  - `src/agentvault_mcp/adapters/openai_adapter.py`
    - Async OpenAI chat adapter; model configurable via `OPENAI_MODEL`.
  - `src/agentvault_mcp/adapters/ollama_adapter.py`
    - Local LLM fallback adapter using Ollama `/api/chat`; configured via
      `OLLAMA_HOST`, `OLLAMA_MODEL`.
  - `src/agentvault_mcp/adapters/web3_adapter.py`
    - AsyncWeb3 wrapper: HTTP provider, `ensure_connection`, `get_nonce`.
  - `src/agentvault_mcp/wallet.py`
    - AgentWalletManager: wallet creation, encrypted key storage, persistence to
      `AGENTVAULT_STORE`, per‑address nonce locks, EIP‑1559 fees, gas
      estimation, balance pre‑checks, spend limits, export (keystore/plaintext
      gated), `simulate_transfer`, `request_faucet_funds`.
  - `src/agentvault_mcp/server.py`
    - MCP stdio server: registers tools, optional prompts/resources, CLI entry
      (`agentvault-mcp`). Zero‑setup defaults (public RPC, persistent key),
      OpenAI/Ollama adapter selection.
  - `src/agentvault_mcp/guardrail.py`
    - Guardrail checker for model outputs: flags banned phrases or missing
      unified diff envelopes.
  - `test_mcp.py`, `test_guardrail.py`
    - Offline tests for context trimming, wallet ops (stubs), spend limits,
      keystore export, and guardrail checks.
  - `docs/prompt-pack.md`
    - Maintainer prompt pack: strict output contract, enforcement nudge, repo
      constraints, and task template.
  - `pyproject.toml`
    - Packaging/entrypoint; optional `mcp` in `dev` extras; setuptools find under
      `src/`.
  - `requirements.txt`
    - Development/test-time dependencies (MCP is optional via extras).
  - `.env.example`
    - Example configuration for keys, limits, store location, faucet URL.
  - `.github/workflows/ci.yml`
    - CI to install deps and run tests.

  ## Environment Variables
  - Core
    - `WEB3_RPC_URL`: Ethereum RPC URL. Default: Sepolia public RPC.
    - `OPENAI_API_KEY`: Enables OpenAI LLM adapter if set.
    - `ENCRYPT_KEY`: Base64 Fernet key. If absent, generated and saved as
      `agentvault_store.key` (sidecar of `AGENTVAULT_STORE`).
    - `AGENTVAULT_STORE`: JSON path for encrypted wallet store (default
      `agentvault_store.json`).
  - LLM
    - `OPENAI_MODEL`: OpenAI model name (default `gpt-4o-mini`).
    - `OLLAMA_HOST`, `OLLAMA_MODEL`: Local LLM fallback config.
  - Safety/Limits
    - `AGENTVAULT_MAX_TX_ETH`: Require confirmation above this amount (ETH).
    - `AGENTVAULT_TX_CONFIRM_CODE`: Server secret needed for high‑value sends.
    - `AGENTVAULT_ALLOW_PLAINTEXT_EXPORT` (0/1) and `AGENTVAULT_EXPORT_CODE` for
      gated plaintext key export (discouraged).
  - Funding
    - `AGENTVAULT_FAUCET_URL`: Faucet endpoint for `request_faucet_funds`.
  - Misc
    - `MCP_MAX_TOKENS`, `LOG_LEVEL`, `TIMEOUT_SECONDS`.

  ## Development
- Run tests: `pytest -q`
- Lint/format: add ruff/black if desired.
  
Note on Python 3.13:
- Some packages (e.g., `tiktoken`) may not ship wheels for Python 3.13.
- This project makes `tiktoken` optional; installation succeeds without it,
  and token counting falls back to a heuristic.

  ## Maintainer Prompt Pack
  - Use docs/prompt-pack.md as your System prompt in an MCP client to enforce
    complete diffs with tests and docs.
  - Guardrail checker:
    - `python -m agentvault_mcp.guardrail reply.txt`
    - exits non‑zero if banned phrases or no unified diff are detected.

  ### Integration with AI Agents

  **Claude Desktop:**
  ```json
  {
    "mcpServers": {
      "autonomous-wallet": {
        "command": "python",
      "args": ["-m", "agentvault_mcp.server"]
      }
    }
  }
  ```

  ### Local LLM (Ollama) Fallback
  - If `OPENAI_API_KEY` is unset, the server prefers a local Ollama instance.
  - Configure via `OLLAMA_HOST` and `OLLAMA_MODEL` (default `llama3.1:8b`).

  **Custom Agent:**
  ```python
  # Agent can now call:
  await agent.call_tool("spin_up_wallet", {"agent_id": "my_agent"})
  await agent.call_tool("execute_transfer", {"agent_id": "my_agent", "to_address": "...", "amount_eth": 0.01})
  ```

  ## Architecture Benefits

  ### For Users
  - **Zero crypto knowledge required**
  - **No API key management**
  - **Automatic wallet creation and funding**
  - **Secure by default**

  ### For Developers
  - **Truly autonomous agents**
  - **No external dependencies**
  - **Production-ready security**
  - **Extensible architecture**

  ### For AI Agents
  - **Full crypto wallet control**
  - **Autonomous decision making**
  - **Real-time blockchain interaction**
  - **Context-aware operations**

  ## What the Agent Can Do Autonomously

  ✅ **Wallet Management**
  - Generate secure HD wallets
  - Encrypt and store private keys
  - Track multiple wallets per user

  ✅ **Funding Operations**
  - Find testnet faucets automatically
  - Suggest exchange options
  - Monitor funding status
  - Calculate optimal funding amounts

  ✅ **Transaction Execution**
  - Sign transactions securely
  - Submit to blockchain
  - Monitor confirmation status
  - Handle gas optimization
  - Prevent replay attacks

  ✅ **Balance Monitoring**
  - Real-time balance checks
  - Low balance alerts
  - Transaction history tracking
  - Portfolio value calculations

  ✅ **Smart Decision Making**
  - Analyze user context
  - Suggest optimal actions
  - Risk assessment
  - Automated rebalancing

  ## Error Handling & Recovery

  The autonomous agent handles errors gracefully:
  - **Network issues**: Automatic retry with exponential backoff
  - **Insufficient funds**: Suggests funding options
  - **Invalid addresses**: Validates before execution
  - **High gas prices**: Waits for optimal conditions
  - **Transaction failures**: Detailed error reporting and recovery

  ## Future Extensions

  The autonomous architecture makes it easy to add:
  - **Multi-chain support** (BSC, Polygon, etc.)
  - **DEX integration** (Uniswap, SushiSwap)
  - **DeFi protocols** (lending, staking, yield farming)
  - **NFT operations** (minting, trading)
  - **Cross-chain bridges**
  - **Portfolio analytics**

  ## Why This Matters

  This plugin represents the future of AI-crypto integration:

  **🤖 True Autonomy**: AI agents that can independently manage crypto wallets
  **🔐 Security First**: Private keys never exposed, all operations local
  **🚀 Zero Friction**: No setup required, works out of the box
  **📈 Scalable**: Architecture supports any blockchain or DeFi protocol
  **🎯 User-Centric**: Designed for users who want AI to handle the complexity

  The agent doesn't just "help" with crypto—it **becomes** your autonomous crypto manager.
  - `src/agentvault_mcp/strategies.py`
    - Stateless strategy helpers (Phase 1): `send_when_gas_below`, `dca_once`.
      Combine simulation, gas checks, and execution into safe one‑shot flows.
  - `src/agentvault_mcp/strategy_manager.py`
    - Stateful strategy manager (Phase 2): create/start/stop/status/tick for DCA
      strategies with interval, gas ceiling, daily caps, and persistence.
