# Wallet MCP Server

A Model Context Protocol (MCP) server that exposes tools for Ethereum wallet management and a context-aware LLM, with structured logging and safe context trimming.

## Features
- ContextManager with proactive trimming and token counting (tiktoken)
- OpenAI adapter (async, configurable model)
- Web3 adapter for ETH balance/transfer (EIP-1559)
- AES-256 symmetric encryption (Fernet) for private keys
- MCP stdio server with tools: `spin_up_wallet`, `query_balance`, `execute_transfer`, `generate_response`

## Quickstart
- Create a virtualenv and install deps:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and fill values:
  - `OPENAI_API_KEY`, `ENCRYPT_KEY`, `WEB3_RPC_URL` (Sepolia recommended)
- Run the server:
  - `python -m wallet_mcp_server`
  - Or install the package and run `wallet-mcp`.

## Environment
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: Model name (default: gpt-4o-mini)
- `ENCRYPT_KEY`: Base64 Fernet key (generate with `Fernet.generate_key()`)
- `WEB3_RPC_URL`: Ethereum RPC (HTTPS)
- `MCP_MAX_TOKENS`: Context token budget (default 4096)
- `LOG_LEVEL`: Logging level (INFO default)

## Development
- Run tests: `pytest -q`
- Linting/formatting are not enforced yet; add ruff/black if desired.

## Notes
- This repo avoids naming collisions with the `mcp` SDK by using the module `wallet_mcp_server.py`.
- Sensitive state (wallet/balance) should not be logged into prompts; scrub before persisting.
