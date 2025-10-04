# AgentVault MCP

<div align="center">
  <h1>🔐 AgentVault MCP</h1>
  <p><strong>Complete Platform for Secure AI Agent Wallet Management</strong></p>
  <p>Production-ready MCP server, Smart Contracts, and Web Dashboard for autonomous crypto operations</p>

  <p>
    <a href="#-installation">📦 Install</a> •
    <a href="#-quick-start">🚀 Quick Start</a> •
    <a href="#-architecture">🏗️ Architecture</a> •
    <a href="#-documentation">📚 Docs</a> •
    <a href="#-examples">💡 Examples</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/Solidity-0.8.19-purple.svg" alt="Solidity 0.8.19">
    <img src="https://img.shields.io/badge/React-18.2-cyan.svg" alt="React 18.2">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License">
    <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg" alt="Production Ready">
    <img src="https://img.shields.io/badge/MCP-21%20Tools-orange.svg" alt="21 MCP Tools">
  </p>
</div>

---

## 🎯 What is AgentVault MCP?

**AgentVault MCP** is a **complete platform** for deploying AI agents with crypto capabilities, consisting of three integrated layers:

### 1️⃣ MCP Server Layer (Core Engine)
Production-ready Model Context Protocol server with **21 MCP tools** for:
- Encrypted wallet management (Fernet encryption)
- EIP-1559 transaction execution
- DeFi strategies (DCA, scheduled sends, micro-tipping)
- Policy enforcement (rate limiting, spend limits)
- Database-backed persistence (PostgreSQL/SQLite)

### 2️⃣ Smart Contract Layer (On-Chain Economy)
**AgentVaultToken (AVT)** - ERC-20 token with usage-based airdrops:
- Pay-per-use billing model (0.01 AVT per API call)
- Automatic airdrops for active users (100+ AVT per 30 days)
- Owner-controlled usage tracking
- Bonus rewards for high usage (up to 1,090 AVT)

### 3️⃣ Dashboard Layer (Web Application)
Full-stack React + FastAPI dashboard with:
- Modern UI with RainbowKit wallet integration
- Real-time usage analytics and cost tracking
- Agent management and monitoring
- Airdrop claim interface
- JWT authentication

---

## ✨ Key Features

### 🔐 Security-First Architecture
- **Military-Grade Encryption**: Fernet (AES-128-CBC + HMAC-SHA256) for private keys
- **Spend Limits**: Configurable thresholds with confirmation codes
- **Multi-Tenancy**: Tenant-scoped database isolation
- **Audit Trail**: Comprehensive event logging for all operations
- **Policy Engine**: YAML-configurable rate limiting per tool/agent

### 🤖 Production-Ready MCP Server
- **21 MCP Tools**: wallet, strategy, and utility operations
- **Async Architecture**: Non-blocking I/O for all RPC and database calls
- **Persistent Storage**: SQLAlchemy + Alembic migrations
- **Structured Logging**: JSON output with `structlog`
- **Comprehensive Testing**: 26 tests with 100% pass rate

### 💰 Token Economics
- **Usage-Based Rewards**: Earn AVT by using the platform
- **Airdrop Formula**: 100 AVT base + bonuses for high usage
- **Anti-Gaming**: 30-day cooldown, minimum 10 API calls
- **Deflationary Mechanism**: User-controlled token burning

### 📊 Strategy System
- **Stateless**: One-shot helpers (send_when_gas_below, dca_once)
- **Stateful**: Persistent scheduled strategies with database state
- **Gas Optimization**: Max base fee thresholds and automatic checks
- **Daily Caps**: Configurable spending limits with automatic resets
- **Dry-Run Mode**: Test strategies without executing transactions

### 🌐 Modern Web Dashboard
- **React 18 + TypeScript**: Type-safe component architecture
- **Web3 Integration**: wagmi + RainbowKit for wallet connections
- **Real-Time Updates**: TanStack Query with 30-second polling
- **Responsive Design**: Mobile-first with Tailwind CSS
- **Charts & Analytics**: Recharts for usage visualization

---

## 🏗️ Architecture

### Complete System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER LAYER                                │
├──────────────────────────────────────────────────────────────────┤
│  MCP Clients         │    Web Browser      │   CLI Tools         │
│  (Claude, Cursor)    │    (Dashboard)      │   (agentvault)      │
└────────┬─────────────┴──────────┬──────────┴──────────┬──────────┘
         │ MCP Protocol           │ REST API             │ Direct
         │ (stdio)                │ (FastAPI)            │ Python
         ▼                        ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │            AgentVault MCP Server (21 Tools)                 │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │  AgentWalletManager  │  StrategyManager               │  │ │
│  │  │  - Fernet encryption │  - DCA scheduling              │  │ │
│  │  │  - Transaction signing│  - Gas optimization           │  │ │
│  │  │  - Nonce management  │  - Daily caps                  │  │ │
│  │  └──────────────┬────────────┬───────────────────────────┘  │ │
│  │                 │            │                               │ │
│  │  ┌──────────────▼────────────▼─────────────────────────────┐│ │
│  │  │          PolicyEngine + Web3Adapter                     ││ │
│  │  │  - Rate limiting      - Async RPC calls                 ││ │
│  │  │  - Event logging      - Gas estimation                  ││ │
│  │  └──────────────┬──────────────────────────────────────────┘│ │
│  └─────────────────┼───────────────────────────────────────────┘ │
│                    │                                              │
└────────────────────┼──────────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
┌────────▼──┐  ┌─────▼──────┐  ┌▼────────────┐
│ PostgreSQL│  │  Ethereum  │  │ Dashboard   │
│ /SQLite   │  │  Network   │  │ (React+TS)  │
│           │  │            │  │             │
│ • Wallets │  │ • AVT Token│  │ • Analytics │
│ • Strats  │  │ • Transfers│  │ • Agents    │
│ • Events  │  │ • Airdrops │  │ • Airdrop   │
│ • Tenants │  │ • Gas fees │  │   UI        │
└───────────┘  └────────────┘  └─────────────┘
```

### Component Breakdown

#### 1. MCP Server Core (`src/agentvault_mcp/`)
- **server.py** (703 lines): FastMCP server with 21 registered tools
- **wallet.py** (597 lines): Secure wallet operations with encryption
- **strategy_manager.py** (313 lines): Persistent strategy lifecycle
- **policy.py** (175 lines): Rate limiting and access control
- **core.py** (160 lines): Context management with token counting

#### 2. Smart Contract (`contracts/AgentVaultToken.sol`)
- **Token**: AVT (AgentVault Token) - ERC-20 compliant
- **Supply**: 1 billion tokens (configurable)
- **Airdrop**: Usage-based rewards every 30 days
- **Security**: ReentrancyGuard + Ownable

#### 3. Dashboard (`dashboard/`)
- **Frontend**: React 18.2 + TypeScript + wagmi + Tailwind
- **Backend**: FastAPI + JWT auth + Pydantic validation
- **Pages**: Dashboard, Agents, Usage, Billing, Wallet, Airdrop, Settings
- **Components**: StatsCard, TokenBalance, UsageChart, RecentActivity

---

## 📦 Installation

### Prerequisites

```bash
# System requirements
Python >= 3.10
Node.js >= 18 (for dashboard)
PostgreSQL >= 13 (recommended for production)
```

### Core Installation

```bash
# 1. Clone repository
git clone https://github.com/axis-ve/AgentVault.git
cd AgentVault

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install with all features
pip install -e '.[ui]'

# 4. Apply database migrations
python -m agentvault_mcp.db.cli upgrade

# 5. Generate encryption key (first time only)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Save output to ENCRYPT_KEY environment variable
```

### Dashboard Installation

```bash
# Frontend
cd dashboard
npm install

# Backend
cd dashboard/backend
pip install -r requirements.txt
```

### Environment Configuration

Create `.env` file:

```bash
# Core Configuration
WEB3_RPC_URL=https://ethereum-sepolia.publicnode.com
ENCRYPT_KEY=<generated-fernet-key>
VAULTPILOT_DATABASE_URL=sqlite+aiosqlite:///agentvault.db

# Security (optional)
AGENTVAULT_MAX_TX_ETH=0.1
AGENTVAULT_TX_CONFIRM_CODE=your-secret-code

# OpenAI (optional)
OPENAI_API_KEY=sk-...

# Smart Contract (after deployment)
AVT_TOKEN_ADDRESS=0x...

# Dashboard Backend
JWT_SECRET_KEY=your-super-secret-jwt-key
```

---

## 🚀 Quick Start

### 1. MCP Server

```bash
# Start MCP server
python -m agentvault_mcp.server

# Or use CLI directly
agentvault-mcp
```

### 2. CLI Usage

```bash
# Create wallet
agentvault create-wallet my-agent

# Check balance
agentvault balance my-agent

# Send transaction (testnet)
agentvault send my-agent 0xRecipientAddress 0.01

# Create DCA strategy
agentvault strategy create my-dca \
  --agent my-agent \
  --to 0xRecipient \
  --amount 0.01 \
  --interval 86400

# Start strategy
agentvault strategy start my-dca

# Tick strategy (execute if due)
agentvault strategy tick my-dca
```

### 3. MCP Client Integration

#### Claude Desktop

Edit `~/.config/claude-desktop/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"],
      "env": {
        "WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com",
        "ENCRYPT_KEY": "your-fernet-key",
        "VAULTPILOT_DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/agentvault"
      }
    }
  }
}
```

**Example Conversation**:
```
You: Create a wallet for my trading bot

Claude: I'll create a wallet for your trading bot.
[Uses spin_up_wallet tool]
✓ Created wallet: 0x742d35Cc6cCc44C4Af2d4C8c4c4c4c4c4c4c4c4c4

You: Send 0.01 ETH to 0x123...

Claude: I'll simulate the transaction first to check gas costs.
[Uses simulate_transfer tool]
Estimated gas: 21000
Estimated fee: 0.000315 ETH
Total cost: 0.010315 ETH

Proceed? Yes

[Uses execute_transfer tool]
✓ Transaction sent: 0xabc123def456...
```

#### Cursor IDE

Add to MCP settings:

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

### 4. Dashboard

```bash
# Start backend
cd dashboard/backend
python main.py  # http://localhost:8000

# Start frontend (new terminal)
cd dashboard
npm start  # http://localhost:3000
```

**Access**: Open http://localhost:3000 in browser

---

## 🛠️ MCP Tools Reference

### Wallet Management (8 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `spin_up_wallet` | Create new encrypted wallet | `spin_up_wallet(agent_id="bot1")` |
| `import_wallet_from_private_key` | Import existing wallet | `import_wallet_from_private_key(agent_id, key)` |
| `import_wallet_from_mnemonic` | Import from seed phrase | `import_wallet_from_mnemonic(agent_id, mnemonic)` |
| `query_balance` | Get ETH balance | `query_balance(agent_id="bot1")` |
| `execute_transfer` | Send ETH transaction | `execute_transfer(agent_id, to, amount)` |
| `simulate_transfer` | Dry-run transaction | `simulate_transfer(agent_id, to, amount)` |
| `sign_message` | Sign arbitrary message | `sign_message(agent_id, message)` |
| `list_wallets` | List all wallets | `list_wallets()` |

### Strategy Tools (8 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `send_when_gas_below` | Conditional send based on gas | `send_when_gas_below(agent_id, to, amount, max_gwei)` |
| `dca_once` | One-time DCA transfer | `dca_once(agent_id, to, amount)` |
| `scheduled_send_once` | Send at specific time | `scheduled_send_once(agent_id, to, amount, iso_time)` |
| `micro_tip_equal` | Split amount equally | `micro_tip_equal(agent_id, recipients, total)` |
| `create_strategy_dca` | Create persistent DCA | `create_strategy_dca(label, agent_id, to, amount, interval)` |
| `start_strategy` | Enable strategy | `start_strategy(label)` |
| `stop_strategy` | Disable strategy | `stop_strategy(label)` |
| `tick_strategy` | Execute strategy if due | `tick_strategy(label)` |

### Utility Tools (5 tools)

| Tool | Description | Example |
|------|-------------|---------|
| `provider_status` | Check RPC connection | `provider_status()` |
| `inspect_contract` | Get contract info | `inspect_contract(address)` |
| `request_faucet_funds` | Request testnet ETH | `request_faucet_funds(agent_id)` |
| `generate_mnemonic` | Create seed phrase | `generate_mnemonic(num_words=12)` |
| `export_wallet_keystore` | Export encrypted JSON | `export_wallet_keystore(agent_id, password)` |

---

## 💰 Token Economics (AVT)

### Airdrop Mechanism

**Eligibility**: 10+ API calls required
**Interval**: 30 days between claims
**Base Reward**: 100 AVT
**Bonus**: +10 AVT per additional 10 calls

**Examples**:
```
10 calls   → 100 AVT
50 calls   → 140 AVT
100 calls  → 190 AVT
500 calls  → 590 AVT
1000 calls → 1090 AVT
```

### Smart Contract Functions

```solidity
// User callable
function claimAirdrop() external returns (uint256 amount);
function burn(uint256 amount) external;

// View functions
function getAirdropInfo(address user) external view returns (
    bool eligible,
    uint256 amount,
    uint256 timeUntilNext
);

function getUserStats(address user) external view returns (
    uint256 totalUsage,
    bool active,
    uint256 lastClaim
);

// Owner only
function recordUsage(address user, uint256 count) external onlyOwner;
function mint(address to, uint256 amount) external onlyOwner;
```

### Deployment

```bash
# Install Hardhat
cd contracts
npm install --save-dev hardhat @openzeppelin/contracts

# Deploy to testnet
npx hardhat run scripts/deploy.js --network sepolia

# Verify on Etherscan
npx hardhat verify --network sepolia <CONTRACT_ADDRESS> <INITIAL_SUPPLY>
```

See [docs/token-economics.md](docs/token-economics.md) for full documentation.

---

## 📊 Use Cases

### 1. AI Trading Bot

```python
# Create trading bot wallet
await wallet_mgr.spin_up_wallet("trading-bot-1")

# Setup DCA strategy
await strategy_mgr.create_strategy_dca(
    label="eth-dca",
    agent_id="trading-bot-1",
    to_address="0xUniswapRouter...",
    amount_eth=0.1,
    interval_seconds=86400,  # Daily
    max_base_fee_gwei=30.0,  # Only buy when gas < 30 gwei
    daily_cap_eth=1.0        # Max 1 ETH per day
)

await strategy_mgr.start_strategy("eth-dca")
```

### 2. Micro-Tipping Bot

```python
# Send equal tips to multiple creators
result = await micro_tip_equal(
    wallet_mgr,
    agent_id="tip-bot",
    recipients=[
        "0xCreator1...",
        "0xCreator2...",
        "0xCreator3..."
    ],
    total_amount_eth=0.03  # 0.01 ETH each
)
```

### 3. Automated Payroll

```python
# Create scheduled payment
await scheduled_send_once(
    wallet_mgr,
    agent_id="payroll-bot",
    to_address="0xEmployee...",
    amount_eth=1.5,
    send_at_iso="2024-02-01T00:00:00Z"
)
```

### 4. Gas-Optimized Transfers

```python
# Send only when gas is cheap
await send_when_gas_below(
    wallet_mgr,
    agent_id="optimizer-bot",
    to_address="0xRecipient...",
    amount_eth=0.5,
    max_base_fee_gwei=20.0  # Wait for < 20 gwei
)
```

---

## 📚 Documentation

### Complete Documentation Set

- **[Architecture Guide](docs/architecture.md)** - System design, data flow, database schema
- **[Token Economics](docs/token-economics.md)** - AVT token, airdrops, smart contracts
- **[Dashboard Guide](docs/dashboard.md)** - React frontend, FastAPI backend, integration
- **[Security Audit](docs/security-audit.md)** - Security considerations, best practices
- **[VaultPilot PRD](docs/vaultpilot_prd.md)** - Product roadmap, SaaS architecture
- **[Agent Guidelines](AGENTS.md)** - Repository standards, development workflow
- **[CLI Guide](docs/cli.md)** - Command-line interface reference
- **[CLAUDE.md](CLAUDE.md)** - Claude Code specific instructions

### API Reference

See [docs/architecture.md#smart-contract-api](docs/architecture.md#smart-contract-api) for complete API documentation.

---

## 🧪 Testing

### Run Tests

```bash
# All tests
pytest -q

# Specific test file
pytest tests/test_wallet_extended.py -v

# With coverage
pytest --cov=src/agentvault_mcp --cov-report=html

# Async tests
pytest tests/test_strategy_manager.py -v
```

### Test Suite

```
tests/
├── test_wallet_extended.py    # Wallet operations, encryption
├── test_strategies.py          # Stateless strategy helpers
├── test_strategy_manager.py    # Persistent strategy lifecycle
├── test_mcp.py                 # MCP tool integration
├── test_policy.py              # Rate limiting, policy engine
├── test_ui.py                  # HTML/QR code generation
└── test_guardrail.py           # Security guardrails
```

**Results**: 26 tests, 100% pass rate

---

## 🔒 Security

### Best Practices

1. **Never Commit Secrets**:
   ```bash
   # Add to .gitignore
   .env
   agentvault_store.*
   *.key
   ```

2. **Use Spend Limits**:
   ```bash
   AGENTVAULT_MAX_TX_ETH=0.1
   AGENTVAULT_TX_CONFIRM_CODE=secret123
   ```

3. **Restrict Plaintext Export**:
   ```bash
   AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=0  # Disabled by default
   ```

4. **Production Database**:
   ```bash
   # Use PostgreSQL, not SQLite
   VAULTPILOT_DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   ```

5. **Multi-Sig for Production**:
   ```bash
   # Transfer AVT token ownership to Gnosis Safe
   token.transferOwnership(SAFE_ADDRESS)
   ```

### Security Audit

See [docs/security-audit.md](docs/security-audit.md) for:
- Critical issues (address immediately)
- High priority items (before production)
- Medium priority items (post-launch)

**Current Grade**: B- (Good for development, needs hardening for production)

---

## 🚢 Deployment

### Development

```bash
# MCP Server
python -m agentvault_mcp.server

# Dashboard (separate terminals)
cd dashboard/backend && python main.py
cd dashboard && npm start
```

### Production (Docker)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agentvault
      POSTGRES_USER: vault
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  mcp-server:
    build: .
    environment:
      VAULTPILOT_DATABASE_URL: postgresql+asyncpg://vault:${DB_PASSWORD}@postgres/agentvault
      WEB3_RPC_URL: ${RPC_URL}
      ENCRYPT_KEY: ${ENCRYPT_KEY}
    depends_on:
      - postgres

  dashboard-backend:
    build: ./dashboard/backend
    environment:
      DATABASE_URL: postgresql+asyncpg://vault:${DB_PASSWORD}@postgres/agentvault
      JWT_SECRET_KEY: ${JWT_SECRET}
    ports:
      - "8000:8000"
    depends_on:
      - postgres

  dashboard-frontend:
    build: ./dashboard
    ports:
      - "80:80"
    depends_on:
      - dashboard-backend

volumes:
  pgdata:
```

```bash
# Deploy
docker-compose up -d
```

---

## 📈 Roadmap

### v0.2.0 (Next)
- [ ] Multi-signature wallet support (Gnosis Safe integration)
- [ ] Cross-chain bridge operations
- [ ] NFT management tools
- [ ] Advanced analytics dashboard
- [ ] Mobile app (React Native)

### v0.3.0 (Future)
- [ ] Layer 2 optimization (Polygon, Arbitrum, Optimism)
- [ ] Social trading features
- [ ] AI strategy optimization
- [ ] Institutional compliance features
- [ ] Plugin ecosystem

### v1.0.0 (Production)
- [ ] Enterprise security (HSM, KMS integration)
- [ ] High availability clustering
- [ ] Audit compliance (SOC 2, ISO 27001)
- [ ] APM integration (Datadog, New Relic)
- [ ] API versioning

See [docs/vaultpilot_prd.md](docs/vaultpilot_prd.md) for complete product roadmap.

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the Repository**
2. **Create Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Make Changes**: Add code + tests
4. **Run Tests**: `pytest`
5. **Commit**: `git commit -m 'feat: add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open Pull Request**

### Commit Convention

```
feat: Add new feature
fix: Bug fix
docs: Documentation changes
test: Add tests
refactor: Code refactoring
chore: Maintenance tasks
```

See [AGENTS.md](AGENTS.md) for detailed contribution guidelines.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support & Community

- **Documentation**: [docs/](docs/)
- **GitHub Issues**: [Issues](https://github.com/axis-ve/AgentVault/issues)
- **Discussions**: [GitHub Discussions](https://github.com/axis-ve/AgentVault/discussions)
- **Twitter**: [@AgentVault](https://twitter.com/AgentVault) (coming soon)

---

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [OpenZeppelin](https://openzeppelin.com/contracts/) - Smart contract library
- [web3.py](https://web3py.readthedocs.io/) - Ethereum Python library
- [RainbowKit](https://www.rainbowkit.com/) - Web3 wallet connection
- [Recharts](https://recharts.org/) - React charting library

---

<div align="center">
  <p><strong>AgentVault MCP</strong> - Empowering AI Agents with Secure Crypto Operations</p>
  <p>Made with ❤️ by the Axis-VE Team</p>
</div>
