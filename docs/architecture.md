# AgentVault MCP Architecture Documentation

## Table of Contents
- [Overview](#overview)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Security Architecture](#security-architecture)
- [Integration Points](#integration-points)

## Overview

AgentVault MCP is a **three-tier architecture** combining:

1. **MCP Server Layer**: Core wallet and strategy engine
2. **Smart Contract Layer**: On-chain token economy
3. **Dashboard Layer**: Full-stack web application

```
┌──────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                           │
├──────────────────────────────────────────────────────────────┤
│  MCP Clients        │    Web Dashboard    │   CLI Tools     │
│  (Claude, Cursor)   │    (React + TS)     │   (Python)      │
└────────┬────────────┴──────────┬──────────┴────────┬─────────┘
         │                       │                    │
         │ MCP Protocol          │ REST API           │ Direct
         │ (stdio)               │ (FastAPI)          │
         ▼                       ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            AgentVault MCP Server                     │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  21 MCP Tools (spin_up_wallet, execute_transfer)│ │   │
│  │  └──────────────┬─────────────────────────────────┘  │   │
│  │                 │                                     │   │
│  │  ┌──────────────▼──────────────┬──────────────────┐  │   │
│  │  │   AgentWalletManager        │ StrategyManager  │  │   │
│  │  │  - Fernet encryption        │ - DCA scheduling │  │   │
│  │  │  - Async nonce management   │ - Gas optimization│ │   │
│  │  │  - Transaction signing      │ - Daily caps     │  │   │
│  │  └──────────────┬──────────────┴──────────────────┘  │   │
│  │                 │                                     │   │
│  │  ┌──────────────▼──────────────────────────────────┐ │   │
│  │  │          PolicyEngine                            │ │   │
│  │  │  - Rate limiting                                 │ │   │
│  │  │  - Event logging                                 │ │   │
│  │  │  - Access control                                │ │   │
│  │  └──────────────┬──────────────────────────────────┘ │   │
│  └─────────────────┼────────────────────────────────────┘   │
│                    │                                         │
└────────────────────┼─────────────────────────────────────────┘
                     │
         ┌───────────▼────────────┐
         │                        │
    ┌────▼─────┐           ┌─────▼────┐
    │ Database │           │ Web3     │
    │ Layer    │           │ Adapter  │
    └────┬─────┘           └─────┬────┘
         │                       │
         ▼                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    PERSISTENCE LAYER                          │
├──────────────────────────────────────────────────────────────┤
│  PostgreSQL/SQLite  │  Ethereum Network  │  Redis (future)  │
│  - Wallets (enc)    │  - AVT Token       │  - Caching       │
│  - Strategies       │  - Transfers       │  - Sessions      │
│  - MCP Events       │  - Airdrops        │                  │
│  - Tenants          │  - Contract calls  │                  │
└──────────────────────────────────────────────────────────────┘
```

## System Components

### 1. MCP Server Layer

**File**: `src/agentvault_mcp/server.py` (703 lines)

**Purpose**: FastMCP-based stdio server exposing 21 MCP tools

**Core Modules**:

#### a. Context Manager (`core.py` - 160 lines)
```python
class ContextManager:
    """Manages conversation history with token counting and trimming"""
    - Token counting with tiktoken (o200k_base encoding)
    - Proactive trimming at 90% capacity
    - Adapter registration (OpenAI, Ollama, Web3)
    - Structured logging with structlog
```

**Features**:
- Automatic context trimming (recency-based)
- Token budget enforcement (default: 4096 tokens)
- Multi-adapter support
- State persistence

#### b. Wallet Manager (`wallet.py` - 597 lines)
```python
class AgentWalletManager:
    """Secure wallet operations with Fernet encryption"""
    - Create/import wallets (private key, mnemonic, keystore)
    - Execute EIP-1559 transactions with gas estimation
    - Sign messages (EIP-191) and typed data (EIP-712)
    - Balance queries and transaction simulation
    - Per-address async locks for nonce management
```

**Security Features**:
- Private keys encrypted with Fernet before database storage
- Spend limits with confirmation codes
- Plaintext export gated behind multiple env vars
- Async locks prevent nonce collisions

#### c. Strategy Manager (`strategy_manager.py` - 313 lines)
```python
class StrategyManager:
    """Persistent strategy lifecycle management"""
    - DCA strategies with interval scheduling
    - Gas price threshold enforcement
    - Daily spending caps with automatic reset
    - Dry-run simulation support
    - Strategy execution audit trail
```

**Strategy Types**:
- **Stateless**: One-shot operations (send_when_gas_below, dca_once, micro_tip)
- **Stateful**: Persistent scheduled strategies (create → start → tick → stop)

#### d. Policy Engine (`policy.py` - 175 lines)
```python
class PolicyEngine:
    """Rate limiting and access control"""
    - Per-tool rate limits (configurable via YAML)
    - Per-agent custom limits
    - Event logging for all tool invocations
    - Real-time enforcement with database tracking
```

**Policy Configuration**:
```yaml
rate_limits:
  default:
    max_calls: 120
    window_seconds: 60
  tools:
    execute_transfer:
      max_calls: 5
      window_seconds: 60
  agents:
    high_frequency_trader:
      max_calls: 1000
      window_seconds: 60
```

#### e. Web3 Adapter (`adapters/web3_adapter.py`)
```python
class Web3Adapter:
    """Async Web3 wrapper with RPC failover"""
    - Async RPC calls (get_balance, send_transaction)
    - Multiple RPC endpoint support
    - Gas estimation (base fee + priority fee)
    - Transaction receipt polling
    - Contract function calls with ABI support
```

### 2. Smart Contract Layer

**File**: `contracts/AgentVaultToken.sol` (152 lines)

**Purpose**: ERC-20 token with usage-based airdrop system

**Contract Details**:
```solidity
contract AgentVaultToken is ERC20, Ownable, ReentrancyGuard {
    // Token: AVT (AgentVault Token)
    // Decimals: 18

    // Core mappings
    mapping(address => uint256) public usageCount;      // API calls
    mapping(address => bool) public isActiveUser;        // 10+ calls
    mapping(address => uint256) public lastAirdrop;      // Claim timestamp

    // Constants
    uint256 public constant AIRDROP_INTERVAL = 30 days;
    uint256 public constant MIN_USAGE_FOR_AIRDROP = 10;
}
```

**Key Functions**:

1. **recordUsage(address user, uint256 count)** - Owner only
   - Records API usage for users
   - Auto-activates users at 10+ calls
   - Emits UsageRecorded event

2. **claimAirdrop()** - User callable
   - Requires active user status
   - 30-day cooldown between claims
   - Amount based on usage: 100 AVT base + bonuses

3. **calculateAirdropAmount(uint256 userUsage)**
   - Base: 100 AVT for 10+ usage
   - Bonus: +10 AVT per additional 10 calls
   - Formula: `100 + ((usage - 10) / 10) * 10`

4. **getAirdropInfo(address user)**
   - Returns: eligible, amount, timeUntilNext
   - View function for dashboard integration

**Airdrop Economics**:
```
Usage:  10 calls  → 100 AVT
Usage:  20 calls  → 110 AVT
Usage:  50 calls  → 140 AVT
Usage: 100 calls  → 190 AVT
```

### 3. Dashboard Layer

#### a. Frontend (`dashboard/src/`)

**Technology Stack**:
- React 18.2 + TypeScript 4.9
- wagmi v1.4 + RainbowKit v1.3 (Web3)
- TanStack Query v5 (state management)
- Tailwind CSS v3.3 (styling)
- Recharts v2.8 (analytics)

**Page Structure**:

1. **Dashboard** (`pages/Dashboard.tsx`)
   - Stats grid (4 metric cards)
   - Usage chart (Recharts line/bar)
   - Recent activity feed
   - Airdrop eligibility alerts
   - Quick actions (create agent, buy tokens)

2. **Agents** (`pages/Agents.tsx`)
   - Agent listing with status
   - Create/update/delete operations
   - Wallet address display
   - Activity tracking

3. **Usage** (`pages/Usage.tsx`)
   - Historical charts (daily/monthly)
   - Cost analysis
   - API call statistics

4. **Billing** (`pages/Billing.tsx`)
   - Billing history
   - Invoice downloads
   - Payment status

5. **Wallet** (`pages/Wallet.tsx`)
   - Token balance (ETH + AVT)
   - Transaction history
   - Transfer functionality

6. **Airdrop** (`pages/Airdrop.tsx`)
   - Eligibility checker
   - Claim interface
   - Next claim countdown

7. **Settings** (`pages/Settings.tsx`)
   - Profile management
   - API keys
   - Security settings

**Key Components**:

```typescript
// StatsCard.tsx
interface StatsCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType;
  trend?: { value: number; isPositive: boolean };
  color: 'blue' | 'green' | 'purple' | 'yellow';
}

// TokenBalance.tsx
- Real-time balance fetching (30s refresh)
- Wallet address with copy-to-clipboard
- Integration with wagmi hooks

// UsageChart.tsx
- Recharts integration
- Multiple chart types (line, bar, area)
- Responsive design
```

**Web3 Configuration** (`config/web3.ts`):
```typescript
// Supported chains
const chains = [mainnet, sepolia];

// RainbowKit wallet connectors
const connectors = connectorsForWallets([
  MetaMask, WalletConnect, Coinbase, ...
]);

// Contract addresses per network
const CONTRACT_ADDRESSES = {
  AGENT_VAULT_TOKEN: {
    [mainnet.id]: '0x...',  // Production
    [sepolia.id]: '0x...',  // Testnet
  },
};
```

#### b. Backend (`dashboard/backend/main.py`)

**Technology Stack**:
- FastAPI (async)
- JWT authentication (HS256)
- bcrypt password hashing
- CORS configured

**API Endpoints**:

```python
# Authentication
POST   /auth/login              # Email/password → JWT token

# Dashboard
GET    /dashboard/stats         # Overview statistics

# Agents
GET    /agents                  # List user's agents
POST   /agents/create           # Create new agent

# Usage & Billing
GET    /usage                   # Usage stats with charts data
GET    /billing/history         # Billing history

# Token & Airdrop
GET    /wallet/balance          # ETH + AVT balance
GET    /airdrop/info            # Eligibility and claim data
POST   /airdrop/claim           # Claim airdrop tokens

# User
GET    /user/profile            # User details and tier
```

**Current State**:
- ⚠️ Mock data (no database yet)
- ⚠️ No MCP integration yet
- ⚠️ No smart contract calls yet
- ✅ Production-ready API structure

## Data Flow

### 1. Wallet Creation Flow

```
User Request (MCP Client)
    │
    ├─► server.spin_up_wallet(agent_id)
    │       │
    │       ├─► AgentWalletManager.spin_up_wallet()
    │       │       │
    │       │       ├─► Account.create() [eth-account]
    │       │       ├─► Fernet.encrypt(private_key)
    │       │       └─► WalletRepository.upsert_wallet()
    │       │               │
    │       │               └─► PostgreSQL INSERT
    │       │
    │       ├─► PolicyEngine.record_event()
    │       │       │
    │       │       └─► EventRepository.record_event()
    │       │               │
    │       │               └─► PostgreSQL INSERT (mcp_events)
    │       │
    │       └─► Return wallet address
    │
    └─► Response: "0x742d35Cc..."
```

### 2. Transaction Execution Flow

```
User Request
    │
    ├─► server.execute_transfer(agent_id, to, amount)
    │       │
    │       ├─► PolicyEngine.enforce() [Rate limit check]
    │       │       │
    │       │       └─► EventRepository.count_events_since()
    │       │               │
    │       │               └─► PostgreSQL SELECT COUNT(*)
    │       │
    │       ├─► AgentWalletManager.execute_transfer()
    │       │       │
    │       │       ├─► _get_wallet_state() [Load from DB]
    │       │       ├─► Fernet.decrypt(encrypted_privkey)
    │       │       ├─► _enforce_spend_limit() [Check confirmation]
    │       │       ├─► Web3Adapter.get_nonce() [Async lock held]
    │       │       ├─► Web3Adapter.estimate_gas()
    │       │       ├─► Account.sign_transaction()
    │       │       ├─► Web3Adapter.send_raw_transaction()
    │       │       ├─► Web3Adapter.wait_for_receipt()
    │       │       └─► WalletRepository.update_last_nonce()
    │       │
    │       ├─► PolicyEngine.record_event() [Success/failure]
    │       │
    │       └─► Return tx_hash
    │
    └─► Response: "0x1234abcd..."
```

### 3. Strategy Tick Flow

```
User/Scheduler Request
    │
    ├─► server.tick_strategy(label)
    │       │
    │       ├─► StrategyManager.tick_strategy()
    │       │       │
    │       │       ├─► StrategyRepository.get_by_label() [Load state]
    │       │       │
    │       │       ├─► Check: strategy.enabled?
    │       │       ├─► Check: strategy.due(now)?
    │       │       ├─► Check: gas < max_base_fee_gwei?
    │       │       ├─► Check: daily_cap not exceeded?
    │       │       │
    │       │       ├─► AgentWalletManager.simulate_transfer()
    │       │       │       │
    │       │       │       └─► Web3Adapter.estimate_gas()
    │       │       │
    │       │       ├─► AgentWalletManager.execute_transfer()
    │       │       │
    │       │       ├─► Update strategy state:
    │       │       │   - last_run_at = now
    │       │       │   - spent_today_eth += amount
    │       │       │   - schedule_next()
    │       │       │
    │       │       ├─► StrategyRunRepository.add_run() [Audit]
    │       │       │
    │       │       └─► Return: {action: "sent", tx_hash, strategy}
    │       │
    │       └─► PolicyEngine.record_event()
    │
    └─► Response: {...}
```

### 4. Airdrop Claim Flow (Future)

```
User (Dashboard)
    │
    ├─► POST /airdrop/claim
    │       │
    │       ├─► Verify JWT token
    │       ├─► Get user's wallet address
    │       │
    │       ├─► Smart Contract Call:
    │       │   AgentVaultToken.claimAirdrop()
    │       │       │
    │       │       ├─► Check: isActiveUser[msg.sender]?
    │       │       ├─► Check: lastAirdrop + 30 days < now?
    │       │       ├─► Calculate amount from usageCount
    │       │       ├─► _transfer(owner, user, amount)
    │       │       └─► lastAirdrop[user] = now
    │       │
    │       └─► Return: {tx_hash, amount}
    │
    └─► Response: "Claimed 100 AVT!"
```

## Database Schema

### Tables

#### 1. wallets
```sql
CREATE TABLE wallets (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    agent_id VARCHAR(255) UNIQUE NOT NULL,
    address VARCHAR(42) NOT NULL,
    encrypted_privkey BYTEA NOT NULL,        -- Fernet encrypted
    chain_id INTEGER NOT NULL,
    last_nonce INTEGER,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wallets_tenant ON wallets(tenant_id);
CREATE INDEX idx_wallets_address ON wallets(address);
```

#### 2. strategies
```sql
CREATE TABLE strategies (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    label VARCHAR(255) UNIQUE NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    strategy_type VARCHAR(64) NOT NULL,      -- "dca", "scheduled", etc.
    to_address VARCHAR(64) NOT NULL,
    amount_eth FLOAT NOT NULL,
    interval_seconds INTEGER,
    enabled BOOLEAN DEFAULT FALSE,
    max_base_fee_gwei FLOAT,
    daily_cap_eth FLOAT,
    next_run_at TIMESTAMP WITH TIME ZONE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    last_tx_hash VARCHAR(120),
    spent_day DATE,
    spent_today_eth FLOAT DEFAULT 0.0,
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_strategies_tenant ON strategies(tenant_id);
CREATE INDEX idx_strategies_agent ON strategies(agent_id);
CREATE INDEX idx_strategies_enabled ON strategies(enabled);
```

#### 3. strategy_runs
```sql
CREATE TABLE strategy_runs (
    id VARCHAR(36) PRIMARY KEY,
    strategy_id VARCHAR(36) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    run_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    result VARCHAR(32) NOT NULL,             -- "sent", "skipped", "failed"
    tx_hash VARCHAR(120),
    detail JSONB
);

CREATE INDEX idx_runs_strategy ON strategy_runs(strategy_id);
CREATE INDEX idx_runs_tenant ON strategy_runs(tenant_id);
```

#### 4. mcp_events
```sql
CREATE TABLE mcp_events (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tool_name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    status VARCHAR(32) NOT NULL,             -- "ok", "error"
    request_payload JSONB,
    response_payload JSONB,
    error_message TEXT
);

CREATE INDEX idx_events_tenant ON mcp_events(tenant_id);
CREATE INDEX idx_events_tool ON mcp_events(tool_name);
CREATE INDEX idx_events_agent ON mcp_events(agent_id);
CREATE INDEX idx_events_occurred ON mcp_events(occurred_at);
```

#### 5. tenants
```sql
CREATE TABLE tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    plan VARCHAR(64) DEFAULT 'starter',      -- "starter", "pro", "enterprise"
    api_key_hash VARCHAR(128) NOT NULL,
    metadata_json JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Migrations

**Alembic-based migrations** in `src/agentvault_mcp/db/migrations/versions/`:

- **0001_initial.py**: Creates wallets, strategies, strategy_runs, mcp_events
- **0002_multi_tenant.py**: Adds tenants table and tenant_id columns

**Apply migrations**:
```bash
python -m agentvault_mcp.db.cli upgrade
```

## Security Architecture

### 1. Encryption at Rest

**Private Keys**:
```python
# Encryption
from cryptography.fernet import Fernet

# Key generation (one-time)
ENCRYPT_KEY = Fernet.generate_key()  # 32 bytes, base64 encoded

# Wallet creation
privkey_bytes = account.key           # 32 bytes
encrypted = Fernet(ENCRYPT_KEY).encrypt(privkey_bytes)
# Stored in database: encrypted_privkey column

# Wallet usage
encrypted = wallet_record.encrypted_privkey
privkey_bytes = Fernet(ENCRYPT_KEY).decrypt(encrypted)
account = Account.from_key(privkey_bytes)
```

**Security Properties**:
- Fernet = AES-128-CBC + HMAC-SHA256
- Authenticated encryption (tampering detected)
- Timestamp included (replay protection)
- Single encryption key per deployment
- Key stored in environment variable (not in code)

### 2. Access Control

**Spend Limits**:
```python
# Environment configuration
AGENTVAULT_MAX_TX_ETH=0.1
AGENTVAULT_TX_CONFIRM_CODE=secret123

# Enforcement in wallet.py
def _enforce_spend_limit(amount_eth, confirmation_code):
    if amount_eth <= threshold:
        return  # Small amounts allowed

    if confirmation_code != AGENTVAULT_TX_CONFIRM_CODE:
        raise WalletError("Confirmation code required for large transfers")
```

**Plaintext Export Protection**:
```python
# Double-gated export
AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1       # Feature flag
AGENTVAULT_EXPORT_CODE=export-secret-456  # Confirmation

# Usage
async def export_wallet_private_key(agent_id, confirmation_code):
    if ALLOW_PLAINTEXT_EXPORT != "1":
        raise WalletError("Export disabled")
    if confirmation_code != EXPORT_CODE:
        raise WalletError("Invalid confirmation")
    return decrypt_and_export(agent_id)
```

### 3. Rate Limiting

**Policy Engine**:
```python
# YAML configuration
rate_limits:
  tools:
    execute_transfer:
      max_calls: 5
      window_seconds: 60

# Enforcement
async def enforce(tool_name, agent_id):
    rule = config.rule_for(tool_name)
    cutoff = now() - timedelta(seconds=rule.window_seconds)
    count = await count_events_since(tool_name, agent_id, cutoff)

    if count >= rule.max_calls:
        raise PermissionError(f"Rate limit exceeded for {tool_name}")
```

### 4. Audit Trail

**Event Logging**:
```python
# Every MCP tool call logged
await policy_engine.record_event(
    tool_name="execute_transfer",
    agent_id="trading-bot",
    status="ok",
    request_payload={"to": "0x...", "amount": 0.01},
    response_payload={"tx_hash": "0x..."},
    error_message=None
)

# Query audit trail
events = await repo.list_events(limit=100)
usage = await repo.aggregate_usage(since=last_24h)
```

### 5. Nonce Management

**Async Locks**:
```python
# Per-address locks prevent nonce collisions
self._locks: Dict[str, asyncio.Lock] = {}

async def execute_transfer(agent_id, to, amount):
    address = wallet_state.address

    async with self._get_lock(address):
        # Critical section: nonce → sign → broadcast
        nonce = await web3.get_nonce(address)
        signed = account.sign_transaction(txn, nonce=nonce)
        tx_hash = await web3.send_raw_transaction(signed)

        # Update persisted nonce
        await repo.update_last_nonce(agent_id, nonce + 1)
```

## Integration Points

### 1. MCP Client Integration

**Claude Desktop** (`~/.config/claude-desktop/claude_desktop_config.json`):
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

### 2. Dashboard ↔ MCP Integration (Future)

**Shared Database Approach**:
```python
# dashboard/backend/main.py
from agentvault_mcp.wallet import AgentWalletManager
from agentvault_mcp.db.repositories import WalletRepository

# Shared database URL
DATABASE_URL = os.getenv("VAULTPILOT_DATABASE_URL")

# Initialize MCP components
ctx = ContextManager()
web3 = Web3Adapter(RPC_URL)
wallet_mgr = AgentWalletManager(ctx, web3, ENCRYPT_KEY, database_url=DATABASE_URL)

@app.post("/agents/create")
async def create_agent(name: str, token_data: dict = Depends(verify_token)):
    # Direct MCP tool call
    address = await wallet_mgr.spin_up_wallet(name)
    return {"wallet_address": address, "name": name}

@app.get("/agents/{agent_id}/balance")
async def get_balance(agent_id: str, token_data: dict = Depends(verify_token)):
    balance = await wallet_mgr.query_balance(agent_id)
    return {"balance_eth": balance}
```

### 3. Smart Contract Integration (Future)

**Backend → Contract Calls**:
```python
# dashboard/backend/main.py
from web3 import Web3
from eth_account import Account

# Load AVT token contract
AVT_ABI = [...]  # ERC-20 + custom functions
avt_address = "0x..."
avt_contract = web3.eth.contract(address=avt_address, abi=AVT_ABI)

@app.post("/airdrop/claim")
async def claim_airdrop(token_data: dict = Depends(verify_token)):
    user_address = token_data["wallet_address"]

    # Check eligibility (on-chain)
    eligible, amount, _ = avt_contract.functions.getAirdropInfo(user_address).call()

    if not eligible:
        raise HTTPException(400, "Not eligible for airdrop")

    # User must sign transaction via frontend
    return {"eligible": True, "amount": amount}

@app.post("/usage/record")
async def record_usage(agent_id: str, count: int, token_data: dict = Depends(verify_token)):
    # Owner-only: Record usage on-chain
    tx = avt_contract.functions.recordUsage(user_address, count).build_transaction({
        "from": OWNER_ADDRESS,
        "nonce": nonce,
    })
    signed = account.sign_transaction(tx)
    tx_hash = web3.eth.send_raw_transaction(signed.rawTransaction)
    return {"tx_hash": tx_hash.hex()}
```

**Frontend → Contract Calls**:
```typescript
// dashboard/src/hooks/useAirdrop.ts
import { useContractWrite, useContractRead } from 'wagmi';
import { AGENT_VAULT_TOKEN_ABI } from '../config/abis';

export function useAirdrop(userAddress: string) {
  // Read eligibility
  const { data: airdropInfo } = useContractRead({
    address: AVT_TOKEN_ADDRESS,
    abi: AGENT_VAULT_TOKEN_ABI,
    functionName: 'getAirdropInfo',
    args: [userAddress],
  });

  // Claim airdrop
  const { write: claimAirdrop } = useContractWrite({
    address: AVT_TOKEN_ADDRESS,
    abi: AGENT_VAULT_TOKEN_ABI,
    functionName: 'claimAirdrop',
  });

  return {
    eligible: airdropInfo?.[0],
    amount: airdropInfo?.[1],
    claimAirdrop,
  };
}
```

### 4. Webhook Integration (Future)

**Event Notifications**:
```python
# src/agentvault_mcp/webhooks.py
class WebhookManager:
    async def notify_transaction(self, event: dict):
        """Send webhook on transaction completion"""
        await httpx.post(
            WEBHOOK_URL,
            json={
                "event": "transaction_completed",
                "agent_id": event["agent_id"],
                "tx_hash": event["tx_hash"],
                "amount_eth": event["amount_eth"],
                "timestamp": event["timestamp"].isoformat(),
            },
            headers={"X-Webhook-Secret": WEBHOOK_SECRET}
        )

    async def notify_airdrop(self, user_address: str, amount: float):
        """Send webhook on airdrop claim"""
        await httpx.post(
            WEBHOOK_URL,
            json={
                "event": "airdrop_claimed",
                "user_address": user_address,
                "amount_avt": amount,
                "timestamp": datetime.now().isoformat(),
            }
        )
```

## Performance Considerations

### 1. Database Optimization

**Connection Pooling**:
```python
# src/agentvault_mcp/db/engine.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Max connections
    max_overflow=10,       # Burst capacity
    pool_pre_ping=True,    # Test connections
    echo=False,            # Disable query logging
)
```

**Query Optimization**:
```python
# Use indexes
CREATE INDEX idx_events_occurred ON mcp_events(occurred_at DESC);

# Efficient counting
SELECT COUNT(*) FROM mcp_events
WHERE tool_name = ? AND agent_id = ? AND occurred_at > ?;
```

### 2. RPC Optimization

**Fallback RPCs**:
```python
# Environment configuration
WEB3_RPC_URLS="https://rpc1.com,https://rpc2.com,https://rpc3.com"

# Automatic failover in Web3Adapter
async def ensure_connection(self):
    for rpc_url in self.rpc_urls:
        try:
            await self.w3.eth.block_number
            self.current_rpc = rpc_url
            return
        except Exception:
            continue
    raise ConnectionError("All RPC endpoints failed")
```

**Batch Requests** (Future):
```python
# Use eth_call batching for multiple reads
from web3.middleware import construct_web3_batch_middleware

web3.middleware_onion.add(construct_web3_batch_middleware)

results = await asyncio.gather(
    web3.eth.get_balance(addr1),
    web3.eth.get_balance(addr2),
    web3.eth.get_balance(addr3),
)
```

### 3. Caching Strategy (Future)

**Redis Integration**:
```python
# Cache balance queries
import aioredis

redis = await aioredis.from_url("redis://localhost")

async def query_balance(agent_id: str) -> float:
    # Check cache (5-second TTL)
    cached = await redis.get(f"balance:{agent_id}")
    if cached:
        return float(cached)

    # Fetch from blockchain
    balance = await web3.eth.get_balance(address)

    # Cache result
    await redis.setex(f"balance:{agent_id}", 5, str(balance))
    return balance
```

## Monitoring and Observability

### 1. Structured Logging

**Configuration**:
```python
# src/agentvault_mcp/core.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger("agentvault_mcp")
```

**Usage**:
```python
logger.info("Wallet created", agent_id=agent_id, address=address)
logger.error("Transfer failed", agent_id=agent_id, error=str(e))
```

### 2. Metrics Collection (Future)

**Prometheus Integration**:
```python
from prometheus_client import Counter, Histogram

# Define metrics
transfers_total = Counter('agentvault_transfers_total', 'Total transfers', ['status'])
transfer_duration = Histogram('agentvault_transfer_duration_seconds', 'Transfer duration')

# Instrument code
@transfer_duration.time()
async def execute_transfer(...):
    try:
        tx_hash = await wallet_mgr.execute_transfer(...)
        transfers_total.labels(status='success').inc()
        return tx_hash
    except Exception:
        transfers_total.labels(status='failure').inc()
        raise
```

### 3. Health Checks

**Endpoint**:
```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "rpc": await check_rpc_connection(),
        "redis": await check_redis(),
    }

    healthy = all(checks.values())
    status_code = 200 if healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if healthy else "unhealthy", "checks": checks}
    )
```

---

## Next Steps

1. **Complete Dashboard Integration**: Connect backend to MCP server and smart contracts
2. **Deploy Smart Contract**: Deploy AVT token to testnet/mainnet
3. **Implement Caching**: Add Redis for performance
4. **Production Hardening**: Address security audit findings
5. **Monitoring**: Set up Prometheus + Grafana
6. **Documentation**: Add API reference and integration guides

For detailed deployment instructions, see [deployment.md](deployment.md).
For security considerations, see [security-audit.md](security-audit.md).
