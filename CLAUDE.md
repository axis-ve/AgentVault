# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- Run all tests: `pytest -q`
- Run specific test file: `pytest test_mcp.py -v`
- Run with async support: Tests use `pytest-asyncio` for async testing

### Development Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

### MCP Server
- Start MCP server: `python -m agentvault_mcp.server` or `agentvault-mcp`
- CLI tool: `agentvault` with various subcommands (see docs/cli.md)

### Code Quality
- No specific linting configured yet - add ruff/black if desired
- Python 3.10+ required, 3.13 supported with optional tiktoken fallback

## Architecture Overview

### Core Components

**MCP Server (`src/agentvault_mcp/server.py`)**
- Entry point for Model Context Protocol stdio server
- Registers all wallet and LLM tools for MCP clients
- Handles initialization of managers and adapters
- Provides both CLI entry point (`agentvault-mcp`) and programmatic server

**Context Manager (`src/agentvault_mcp/core.py`)**
- `ContextManager`: handles conversation history, token counting, proactive trimming
- Uses tiktoken when available, falls back to heuristic counting if not installed
- Structured logging setup with configurable levels
- `ContextSchema`: Pydantic model for conversation state validation

**Wallet Manager (`src/agentvault_mcp/wallet.py`)**
- `AgentWalletManager`: secure wallet operations with Fernet encryption
- Per-agent wallet creation and management
- EIP-1559 transaction support with gas estimation
- Async nonce management with per-address locks to prevent races
- Encrypted key storage with persistence to `AGENTVAULT_STORE`
- Safety features: spend limits, confirmation codes for high-value transfers

**Web3 Adapter (`src/agentvault_mcp/adapters/web3_adapter.py`)**
- `Web3Adapter`: async wrapper around web3.py
- RPC connection management with fallback rotation support
- Network detection and gas price estimation

**LLM Adapters**
- `OpenAIAdapter` (`src/agentvault_mcp/adapters/openai_adapter.py`): async OpenAI integration
- `OllamaAdapter` (`src/agentvault_mcp/adapters/ollama_adapter.py`): local LLM fallback

### Strategy System

**Stateless Strategies (`src/agentvault_mcp/strategies.py`)**
- One-shot strategy helpers: `send_when_gas_below`, `dca_once`, `scheduled_send_once`
- Micro-tipping utilities: `micro_tip_equal`, `micro_tip_amounts`
- Combine simulation, validation, and execution in safe flows

**Stateful Strategy Manager (`src/agentvault_mcp/strategy_manager.py`)**
- `StrategyManager`: persistent strategy lifecycle management
- Create/start/stop/tick operations for long-running strategies
- Interval scheduling with gas limits and daily caps
- State persistence for strategy execution tracking

### Additional Components

**CLI (`src/agentvault_mcp/cli.py`)**
- Command-line interface with wallet and strategy operations
- Supports all core wallet functions plus strategy execution
- UI generation: tip-jar QR codes, HTML pages, dashboard

**UI Generation (`src/agentvault_mcp/ui.py`, `src/agentvault_mcp/tipjar.py`)**
- Static HTML generation for tip jars and dashboards
- QR code generation for Ethereum payment URIs
- Brutalist styling with theme toggle support

## Key Design Patterns

### Security Model
- Private keys encrypted with Fernet, never stored in plaintext
- Confirmation codes required for high-value transactions (`AGENTVAULT_MAX_TX_ETH`)
- Plaintext key export gated behind multiple environment variables
- Address uniqueness checks to prevent wallet reuse

### Async Architecture
- All I/O operations are async (RPC calls, LLM requests)
- Proper nonce management with async locks per wallet address
- Context-aware error handling with structured logging

### Configuration
- Environment-driven configuration with sensible defaults
- Auto-generation of encryption keys if not provided
- Fallback RPC support for reliability
- Optional dependencies (tiktoken, MCP) with graceful degradation

### Testing Strategy
- Offline tests that don't hit external services
- Mock/stub usage for RPC and API calls
- pytest-asyncio for async test support
- Focus on wallet operations, context management, and strategy logic

## Environment Variables Reference

### Core Configuration
- `WEB3_RPC_URL`: Primary Ethereum RPC URL (default: Sepolia public)
- `WEB3_RPC_URLS`: Comma-separated backup RPCs for fallback
- `OPENAI_API_KEY`: OpenAI API key (optional, enables OpenAI adapter)
- `ENCRYPT_KEY`: Base64 Fernet key (auto-generated if missing)
- `AGENTVAULT_STORE`: Wallet storage path (default: agentvault_store.json)

### Safety Limits
- `AGENTVAULT_MAX_TX_ETH`: Require confirmation above this amount
- `AGENTVAULT_TX_CONFIRM_CODE`: Confirmation code for high-value sends
- `AGENTVAULT_ALLOW_PLAINTEXT_EXPORT`: Enable plaintext key export (0/1)
- `AGENTVAULT_EXPORT_CODE`: Confirmation code for plaintext export

### Optional Features
- `AGENTVAULT_FAUCET_URL`: Testnet faucet endpoint
- `OLLAMA_HOST`, `OLLAMA_MODEL`: Local LLM configuration
- `MCP_MAX_TOKENS`, `LOG_LEVEL`, `TIMEOUT_SECONDS`: Performance tuning

## Development Guidelines

### Code Style
- Target Python 3.10+ compatibility
- Async/await for all I/O operations
- Structured logging with contextual information
- Type hints and Pydantic models for data validation

### Security Considerations
- Never log or expose private keys or sensitive data
- Use confirmation codes for destructive operations
- Validate all user inputs (addresses, amounts, etc.)
- Implement proper error handling without information leakage

### Testing Requirements
- All new features must include offline tests
- Use mocks/stubs for external services (RPC, APIs)
- Test error conditions and edge cases
- Maintain async test compatibility with pytest-asyncio

### Error Handling
- Use custom exceptions: `MCPError`, `WalletError`, `ContextOverflowError`
- Provide clear, actionable error messages
- Log errors with structured context for debugging
- Graceful degradation for optional features