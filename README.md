# AgentVault MCP

AgentVault MCP is an MCP-native toolkit that lets autonomous agents create and operate encrypted Ethereum wallets, orchestrate strategies, and interact with DeFi protocols without exposing private keys. The project ships a stdio MCP server, a CLI, and composable Python helpers that share the same runtime code paths.

## Highlights

- **Secure wallet orchestration** – Fernet-encrypted keystores persisted on disk, configurable limits, faucet helpers, and keystore exports for backup.
- **Dynamic chain metadata** – Uniswap and Aave deployments are resolved per chain at startup (Ethereum, Base, Arbitrum, Sepolia) so new networks can be toggled via environment configuration without code changes.
- **Universal Router support** – Sepolia swaps use Uniswap’s Universal Router with automatic Permit2 and ERC‑20 approvals before broadcasting real transactions.
- **Strategy automation** – Stateless helpers (`dca_once`, `send_when_gas_below`, `micro_tip_*`) and a stateful scheduler (`StrategyManager`) for recurring operations.
- **Network inspection** – Query RPC health and inspect deployed contracts (bytecode, ERC-20 metadata) directly from MCP or the CLI.
- **MCP-first architecture** – Every capability is exposed as an MCP tool; the CLI simply calls the server, ensuring identical behaviour in headless agent deployments.

## Requirements

- Python ≥ 3.10
- Access to an Ethereum JSON-RPC endpoint (Sepolia public RPC works by default)
- Optional: OpenAI or Ollama keys for LLM prompt trimming tools

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

To work on HTML/dashboard helpers:

```bash
pip install 'agentvault-mcp[ui]'
```

## Configuration

AgentVault loads configuration from environment variables; create an `.env` file for local development.

| Variable | Description | Default |
| --- | --- | --- |
| `WEB3_RPC_URL` | RPC endpoint (HTTP) | `https://ethereum-sepolia.publicnode.com` |
| `ENCRYPT_KEY` | Base64 Fernet key. If omitted, a key/JSON store pair is created next to the store. | auto-generate |
| `AGENTVAULT_STORE` | Path to wallet store JSON | `agentvault_store.json` |
| `AGENTVAULT_STRATEGY_STORE` | Path to strategy schedule JSON | `agentvault_strategies.json` |
| `AGENTVAULT_MAX_TX_ETH` | Spend threshold requiring confirmation codes | unset |
| `AGENTVAULT_TX_CONFIRM_CODE` | Server-side confirmation code | unset |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | LLM response generation | unset |
| `AGENTVAULT_FAUCET_URL` | Optional JSON faucet endpoint | unset |

Sepolia DeFi requires no extra setup. Mainnet/Base/Arbitrum reuse legacy V3 routers until Universal Router data is published.

## Usage

### Start the MCP server

```bash
source .venv/bin/activate
python -m agentvault_mcp.server
```

The server exposes 21 MCP tools. Connect from Claude Desktop, Cursor, or any MCP client by pointing them at the stdio command above.

### CLI shortcuts

```bash
# create & inspect
agentvault create-wallet mybot
agentvault balance mybot

# simulate / send
agentvault simulate mybot 0xRecipient... 0.01
agentvault send mybot 0xRecipient... 0.01 --confirmation-code changeme

# strategies
agentvault strategy dca-once mybot 0xRecipient... 0.01
agentvault strategy send-when-gas-below mybot 0xRecipient... 0.01 25

# DeFi (Sepolia Universal Router)
agentvault swap-tokens mybot WETH USDC 0.001 --dry-run
agentvault swap-tokens mybot WETH USDC 0.001   # executes Permit2 + swap

# inspection
agentvault provider-info
agentvault inspect-contract 0xUniversalRouterAddress
```

Key MCP tools mirror the CLI surface: `provider_status` reports chain ID, client
version, base fee, and latest block data; `inspect_contract` fetches bytecode
length, on-chain balance, and best-effort ERC-20 metadata when available.

### DeFi specifics

- Chain metadata is fetched on demand (`src/agentvault_mcp/network_config.py`). Sepolia pulls Universal Router/Permit2 deployments from Uniswap’s repository and Aave pool addresses from the official `aave-address-book` repo.
- `execute_swap` automatically:
  1. Computes a price quote from the live v3 pool state.
  2. Ensures the ERC‑20 token is approved for Permit2.
  3. Confirms/extends the Permit2 allowance.
  4. Broadcasts the Universal Router command (`execute(commands, inputs, deadline)`).
- Dry runs return a payload containing the command bytes, deadline, and allowance state without sending transactions.

## Development

### Formatting & lint

The project relies on the existing repo standards (pytest, async fixtures). Before opening a PR:

```bash
pip install -e .[dev]
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q
```

### Dynamic chain configs

`load_chain_config(chain_id)` resolves network data. To add a new chain, extend the loader with the appropriate Uniswap/Aave metadata or a custom configuration file.

### Project structure

- `src/agentvault_mcp/core.py` – context trimming + adapter registry
- `src/agentvault_mcp/wallet.py` – encrypted wallet manager with persistence
- `src/agentvault_mcp/strategies.py` – stateless strategy helpers
- `src/agentvault_mcp/strategy_manager.py` – persistent scheduler
- `src/agentvault_mcp/defi.py` – DeFi operations (now universal-router aware)
- `src/agentvault_mcp/network_config.py` – dynamic chain metadata
- `src/agentvault_mcp/server.py` – MCP stdio server

## Testing guide

- Use `make test` or `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest` for the full suite.
- `test_defi_tools.py` demonstrates the Sepolia DeFi workflow and matches the live behaviour verified during manual testing.
- For on-chain validation, fund the Sepolia demo wallet with ETH, wrap a small amount into WETH, then call `swap_tokens` with `dry_run=False` to watch Permit2 + Universal Router transactions land.

## Contributing

1. Fork and create a feature branch.
2. Follow the repo’s PEP8 + type-hint conventions.
3. Add tests where behaviour changes or new guardrails are introduced.
4. Run the pytest suite before submitting PRs.
5. Document environment variables or breaking changes in the README.

## License

MIT License © Axis VE Studio
