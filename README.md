# AgentVault MCP

[![PyPI](https://img.shields.io/pypi/v/agentvault-mcp.svg)](https://pypi.org/project/agentvault-mcp/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue.svg)](#)
[![CI](https://github.com/axis-ve/AgentVault/actions/workflows/ci.yml/badge.svg)](https://github.com/axis-ve/AgentVault/actions/workflows/ci.yml)
[![Release](https://github.com/axis-ve/AgentVault/actions/workflows/release.yml/badge.svg)](https://github.com/axis-ve/AgentVault/actions/workflows/release.yml)
[![GitHub Release](https://img.shields.io/github/v/release/axis-ve/AgentVault?include_prereleases&label=github)](https://github.com/axis-ve/AgentVault/releases)

Secure context and wallet tools for autonomous AI agents, built on the Model Context Protocol (MCP). Exposes stdio MCP tools for Ethereum wallet management and a context-aware LLM, with structured logging and safe context trimming.

## MCP‑First Philosophy
- The MCP server and tools are the core engine. Integrate with Claude Desktop, Cursor, Claude Code, or your own agents to drive wallet ops, transfers, and strategies.
- UI helpers are optional utilities for convenience only; agents should primarily call MCP tools and resources.

## 🚀 Quick Start for New Users

### 1. Installation
```bash
git clone https://github.com/axis-ve/AgentVault.git
cd AgentVault
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

### 2. Basic Usage (No Setup Required)
```bash
# Start MCP server (works with public testnet RPC)
python -m agentvault_mcp.server

# Or use CLI directly
agentvault create-wallet agent1
agentvault balance agent1
agentvault send agent1 0x1234...5678 0.001
```

### 3. MCP Client Integration

**Claude Desktop** (add to `~/.config/claude-desktop/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"],
      "env": {
        "WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com"
      }
    }
  }
}
```

**Cursor IDE** (MCP settings):
```json
{
  "mcp": {
    "servers": {
      "agentvault": {
        "command": "agentvault-mcp",
        "env": {
          "WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com"
        }
      }
    }
  }
}
```

**Claude Code** (`.claude/settings.json`):
```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"]
    }
  }
}
```

### 4. What You Get
- **21 MCP Tools** for wallet operations, transfers, DCA strategies
- **Secure Wallet Management** with encrypted private keys
- **Optional UI** helpers (CLI + MCP tools) for tip jars and dashboards
- **Context-Aware LLM** integration with automatic trimming
- **Production Ready** with comprehensive error handling and testing

### 5. Core Workflows
  ```bash
  # Create wallet and check balance
  agentvault create-wallet myagent
  agentvault balance myagent
  
  # Generate tip jar page
  agentvault tip-jar-page myagent --amount 0.01 --out tipjar.html

  # Setup DCA strategy
  agentvault strategy dca-once myagent 0x1234...5678 0.001
  ```

### Optional UI Extra
For QR/HTML generation, install the optional UI extra:
```bash
pip install 'agentvault-mcp[ui]'
```

## 🎯 Real-World Use Cases

### For Individual Users

#### **Personal Crypto Automation**
```bash
# Set up automated DCA to your favorite project
agentvault create-wallet my-dca-bot
agentvault strategy dca-once my-dca-bot 0x742d35Cc6634C0532925a3b8D400C1a4Cfa3c64d 0.01
```
Automatically send small amounts weekly to creators, projects, or causes without manual intervention.

#### **Content Creator Monetization**
```bash
# Generate a tip jar page for your content
agentvault create-wallet creator-wallet
agentvault tip-jar-page creator-wallet --amount 0.005 --out tipjar.html
```
Add crypto tipping to blogs, streams, or social media with QR codes.

#### **Smart Gas Optimization**
```bash
# Only send when gas is cheap
agentvault strategy send-when-gas-below my-wallet 0x123...abc 0.1 20
```
Save money on transaction fees by automatically waiting for optimal gas conditions.

### For AI/Agent Developers

#### **Autonomous Agent Operations**
```python
# AI agent can autonomously manage wallets and funds
await agent.call_tool("spin_up_wallet", {"agent_id": "trading-bot"})
await agent.call_tool("execute_transfer", {
    "agent_id": "trading-bot",
    "to_address": "0xDeFiProtocol...",
    "amount_eth": 0.1
})
```
Build AI agents that can buy/sell tokens, provide liquidity, or rebalance portfolios.

#### **Multi-Agent Coordination**
```python
# Create specialized agent wallets for different roles
agents = ["collector", "distributor", "treasury"]
for agent in agents:
    await session.call_tool("spin_up_wallet", {"agent_id": agent})

# Distributor pays multiple recipients automatically
await session.call_tool("micro_tip_equal", {
    "agent_id": "distributor",
    "addresses": ["0xCreator1...", "0xCreator2..."],
    "total_amount_eth": 0.5
})
```

### For IDE Users (Claude Code/Cursor)

#### **Development Workflow Integration**
Ask your AI assistant:
- "Create a test wallet for our dApp integration tests"
- "Send some testnet ETH to our smart contract for testing"
- "Generate a payment page for our SaaS billing"
- "Set up automated payments to our team members"

#### **Rapid Prototyping**
- "Create wallets for Alice, Bob, and Charlie, then simulate a 3-way payment split"
- "Build a tip jar component for our React app"
- "Test our smart contract by sending it some ETH"

### For Small Businesses

#### **Automated Payroll**
```bash
# Pay team members automatically
agentvault strategy micro-tip-amounts payroll-bot "alice.eth=0.5,bob.eth=0.3"
```

#### **Subscription Services**
Monitor payments and manage access automatically with AI agents.

#### **Donation Management**
```bash
# Create donation pages with QR codes
agentvault tip-jar-page charity-wallet --amount 0.02 --out donate.html
```

## 🔧 Core Capabilities

### What Actually Works
- **✅ HD Wallet Creation** - Secure Ethereum wallets with encrypted private keys
- **✅ Real ETH Transfers** - EIP-1559 transactions with gas optimization
- **✅ Balance Monitoring** - Real-time ETH balance queries
- **✅ Advanced Strategies** - DCA, gas optimization, scheduled transfers, micro-tipping
- **✅ MCP Integration** - 21 tools for Claude Desktop, Cursor IDE, Claude Code
- **✅ UI Generation** - HTML tip jars and dashboards with QR codes
- **✅ Production Security** - Encrypted storage, spend limits, confirmation codes

### Key Features
- **MCP-First Architecture** - 21 tools for autonomous AI agent operations
- **Zero-Config Setup** - Works with public testnet RPC out of the box
- **Context-Aware LLM** - Built-in OpenAI/Ollama integration
- **Persistent Strategies** - Long-running automated operations with state management
- **Security by Design** - Private keys encrypted with Fernet, never exposed
- **Multi-Strategy Support** - Gas optimization, DCA, scheduled sends, batch payments

## 📋 Getting Started Guide

### Step-by-Step Workflow
1. **Start MCP server**: `python -m agentvault_mcp.server`
2. **Create wallet**: `spin_up_wallet(agent_id)` → returns address
3. **Fund wallet**: `request_faucet_funds(agent_id)` or fund manually
4. **Test transfer**: `simulate_transfer(agent_id, to_address, amount_eth)`
5. **Execute transfer**: `execute_transfer(agent_id, to_address, amount_eth)`
6. **Export backup**: `export_wallet_keystore(agent_id, passphrase)`

### For Auditors & Security Reviewers
- **Private keys** encrypted with Fernet, never stored in plaintext
- **Spend limits** configurable via `AGENTVAULT_MAX_TX_ETH`
- **Confirmation codes** required for high-value transfers
- **Comprehensive logging** for audit trails
- **Testnet-first** approach for safe development
- **Open source** - full code available for security review

## 👥 For Newcomers

### What This Tool Actually Does
AgentVault MCP enables **AI agents to autonomously manage Ethereum wallets**. Think of it as giving your AI assistant the ability to:
- Create and manage crypto wallets securely
- Send and receive ETH transactions automatically
- Optimize gas fees and timing
- Handle recurring payments (DCA strategies)
- Generate payment pages with QR codes

### Why This Matters
This is the first tool that lets AI agents handle **real money operations** autonomously while maintaining security. No more "AI assistants that can only talk" - now they can actually execute financial operations.

### Is It Safe?
Yes - designed with security as the top priority:
- Private keys encrypted with military-grade encryption
- Spend limits and confirmation codes for large amounts
- Testnet-first approach for safe development
- Open source for full transparency and audits

### What's the Catch?
None - this is a public good tool released under MIT license. Use it freely for personal projects, commercial applications, or research.

## 🛠 Developer Integration

AgentVault MCP provides three integration methods:

### 1. MCP Clients (Recommended)
Connect to Claude Desktop, Cursor IDE, or Claude Code for AI-driven wallet operations.

### 2. Direct Python API
```python
import asyncio
from agentvault_mcp.core import ContextManager
from agentvault_mcp.adapters.web3_adapter import Web3Adapter
from agentvault_mcp.wallet import AgentWalletManager

async def create_and_fund_wallet():
    ctx = ContextManager()
    w3 = Web3Adapter("https://ethereum-sepolia.publicnode.com")
    mgr = AgentWalletManager(ctx, w3, "your-encrypt-key")

    # Create wallet
    address = await mgr.spin_up_wallet("my-agent")
    print(f"Created wallet: {address}")

    # Check balance and simulate transfer
    balance = await mgr.query_balance("my-agent")
    sim_result = await mgr.simulate_transfer("my-agent", "0x742d35Cc...", 0.001)

asyncio.run(create_and_fund_wallet())
```

### 3. CLI Commands
```bash
# Basic wallet operations
agentvault create-wallet <agent_id>
agentvault list-wallets
agentvault balance <agent_id>
agentvault send <agent_id> <to_address> <amount>

# Advanced strategies
agentvault strategy dca-once <agent_id> <to_address> <amount>
agentvault strategy send-when-gas-below <agent_id> <to> <amount> <max_gwei>
agentvault strategy micro-tip-equal <agent_id> <addr1,addr2,...> <total_amount>

# UI generation
agentvault tip-jar-page <agent_id> --amount 0.01 --out page.html
agentvault dashboard --out dashboard.html

# Backup and export
agentvault export-keystore <agent_id> <passphrase>
```

## 🔧 Available MCP Tools (21 Total)

### Core Wallet Operations
- `spin_up_wallet(agent_id)` - Create secure HD wallet with encrypted private key
- `query_balance(agent_id)` - Get real-time ETH balance
- `execute_transfer(agent_id, to_address, amount_eth)` - Send ETH with EIP-1559 optimization
- `simulate_transfer(agent_id, to_address, amount_eth)` - Dry-run transfers with gas estimation
- `list_wallets()` - Get all agent wallets (addresses only, no keys)

### Advanced Strategies
- `send_when_gas_below(agent_id, to_address, amount_eth, max_base_fee_gwei)` - Conditional sends
- `dca_once(agent_id, to_address, amount_eth)` - Dollar cost averaging transfers
- `micro_tip_equal(agent_id, addresses, total_amount_eth)` - Split payments equally
- `micro_tip_amounts(agent_id, address_amounts)` - Custom amount splits

### Persistent Strategy Management
- `create_strategy_dca(label, agent_id, to_address, amount_eth, interval_seconds)` - Create recurring DCA
- `start_strategy(label)`, `stop_strategy(label)` - Control strategy execution
- `tick_strategy(label)` - Execute strategy if conditions met
- `list_strategies()`, `delete_strategy(label)` - Manage strategies

### Utility Tools
- `generate_tipjar_page(agent_id, amount_eth)` - Create HTML tip jar with QR code
- `generate_dashboard_page()` - Create wallet/strategy overview dashboard
- `export_wallet_keystore(agent_id, passphrase)` - Export encrypted V3 keystore
- `request_faucet_funds(agent_id)` - Get testnet ETH (if faucet configured)
- `generate_response(user_message)` - Context-aware LLM integration

## 🔒 Security & Configuration

### Security Features
- **Encrypted private keys** with Fernet (military-grade encryption)
- **Auto-generated encryption keys** if not provided
- **Spend limits** via `AGENTVAULT_MAX_TX_ETH` with confirmation codes
- **Keystore export** preferred over plaintext (V3 standard)
- **Cryptographic randomness** for wallet generation
- **Sanitized context** - no private keys in logs or resources

### Key Environment Variables
```bash
# Core configuration
WEB3_RPC_URL=https://ethereum-sepolia.publicnode.com  # Default: public testnet
ENCRYPT_KEY=your-base64-fernet-key  # Auto-generated if not set
AGENTVAULT_STORE=agentvault_store.json  # Encrypted wallet storage

# Security limits
AGENTVAULT_MAX_TX_ETH=0.1  # Require confirmation above this amount
AGENTVAULT_TX_CONFIRM_CODE=your-secret-code  # For high-value transfers

# LLM integration (optional)
OPENAI_API_KEY=sk-your-key  # Enables AI context features
OPENAI_MODEL=gpt-4o-mini  # Default model
```

## 🏗 Architecture Overview

### Core Components
- **`server.py`** - MCP stdio server with 21 registered tools
- **`wallet.py`** - Secure HD wallet management with encryption
- **`strategies.py`** - Advanced automation (DCA, gas optimization, scheduling)
- **`ui.py`** - HTML/QR code generation for payment interfaces
- **`core.py`** - Context management and LLM integration

### Security Architecture
- **Fernet encryption** for all private key storage
- **EIP-1559 gas optimization** with automatic fee calculation
- **Spend limits and confirmation codes** for high-value operations
- **Testnet-first development** with production-ready security

## 📚 Additional Documentation

- **[User Onboarding Guide](docs/user-onboarding.md)** - Step-by-step setup for new users
- **[MCP Integration Examples](docs/mcp-integration-examples.md)** - Detailed client integration patterns
- **[CLAUDE.md](CLAUDE.md)** - Technical guidance for AI development

## 🚀 What's New in v0.1.1

**First Official Working Release** - All previous versions had runtime issues
- ✅ **MCP SDK Compatibility** - Works with FastMCP (MCP SDK v1.14.0+)
- ✅ **Security Hardening** - Auto-generated encryption keys with safe fallbacks
- ✅ **Production Ready** - All 21 MCP tools fully functional
- ✅ **Comprehensive Testing** - Core functionality verified and tested
- ✅ **Optional UI Extras** - `pip install 'agentvault-mcp[ui]'` for QR generation

## 📄 License & Contributing

Released under MIT License - use freely for personal or commercial projects.
This is a public good tool designed to advance AI-crypto integration.

**Contributing**: Open issues and pull requests welcome. See [CLAUDE.md](CLAUDE.md) for development guidelines.

---

*AgentVault MCP - Enabling autonomous AI agents to manage real crypto wallets securely. The first tool that lets AI handle money operations while maintaining enterprise-grade security.*
