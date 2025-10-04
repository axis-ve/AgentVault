# AgentVault Dashboard - Complete Documentation

## Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Frontend Application](#frontend-application)
- [Backend API](#backend-api)
- [Integration Guide](#integration-guide)
- [Deployment](#deployment)
- [Development Guide](#development-guide)

## Overview

The AgentVault Dashboard is a modern, full-stack web application for managing AI agents, tracking usage, and interacting with the token economy. It provides a user-friendly interface for all AgentVault MCP functionality.

### Features

**Core Functionality**:
- 🎯 **Modern React Dashboard** - Clean, responsive UI with real-time updates
- 💰 **Token-Based Economy** - Pay for agent services using AVT tokens
- 🔗 **Wallet Integration** - Connect Web3 wallets (MetaMask, WalletConnect, etc.)
- 🤖 **Agent Management** - Create, monitor, and manage AI agents
- 📊 **Usage Analytics** - Real-time usage statistics and cost tracking
- 🎁 **Airdrop System** - Earn tokens by actively using the platform

**Technical Highlights**:
- React 18.2 + TypeScript 4.9
- wagmi + RainbowKit for Web3
- TanStack Query for state management
- FastAPI async backend
- JWT authentication
- Real-time updates

## Architecture

### System Design

```
┌────────────────────────────────────────────────────────┐
│                  Browser (User)                        │
└────────────────────┬───────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────┐       ┌────────▼────────┐
│  React Frontend│       │  MetaMask/WC    │
│  (TypeScript)  │       │  Wallet         │
└───────┬────────┘       └────────┬────────┘
        │                         │
        │ REST API                │ Web3 RPC
        │                         │
┌───────▼─────────────────────────▼────────┐
│          FastAPI Backend                 │
│  ┌────────────────────────────────────┐  │
│  │  Authentication (JWT)              │  │
│  │  Rate Limiting                     │  │
│  │  CORS                              │  │
│  └────────┬───────────────────────────┘  │
└───────────┼──────────────────────────────┘
            │
    ┌───────┼───────┐
    │               │
┌───▼────┐   ┌──────▼──────┐   ┌────────────┐
│Database│   │ MCP Server  │   │ Blockchain │
│(SQLite)│   │ (Future)    │   │ (Ethereum) │
└────────┘   └─────────────┘   └────────────┘
```

### Technology Stack

#### Frontend
```json
{
  "framework": "React 18.2",
  "language": "TypeScript 4.9",
  "web3": {
    "wagmi": "1.4.7",
    "rainbowKit": "1.3.0",
    "ethers": "6.8.1"
  },
  "state": {
    "reactQuery": "5.8.4"
  },
  "styling": {
    "tailwindcss": "3.3.5",
    "headlessui": "1.7.17",
    "heroicons": "2.2.0"
  },
  "charts": {
    "recharts": "2.8.0"
  },
  "routing": {
    "reactRouter": "6.18.0"
  },
  "animation": {
    "framerMotion": "10.16.5"
  }
}
```

#### Backend
```python
{
    "framework": "FastAPI",
    "auth": "JWT (HS256)",
    "password": "bcrypt",
    "validation": "Pydantic",
    "cors": "FastAPI middleware",
    "server": "Uvicorn"
}
```

## Frontend Application

### Project Structure

```
dashboard/src/
├── components/           # Reusable UI components
│   ├── Layout.tsx       # Main layout with navigation
│   ├── StatsCard.tsx    # Statistics display cards
│   ├── TokenBalance.tsx # Wallet balance component
│   ├── UsageChart.tsx   # Usage analytics charts
│   └── RecentActivity.tsx # Activity feed
│
├── pages/               # Main application pages
│   ├── Dashboard.tsx    # Main dashboard
│   ├── Agents.tsx       # Agent management
│   ├── Usage.tsx        # Usage analytics
│   ├── Billing.tsx      # Billing and payments
│   ├── Wallet.tsx       # Wallet management
│   ├── Airdrop.tsx      # Airdrop claims
│   └── Settings.tsx     # User settings
│
├── config/              # Configuration files
│   └── web3.ts          # Web3 and wallet config
│
├── hooks/               # Custom React hooks
│   └── useAirdrop.ts    # Airdrop hook (example)
│
├── utils/               # Utility functions
│
├── App.tsx              # Root component
├── index.js             # Entry point
└── index.css            # Global styles
```

### Key Components

#### 1. Layout Component

**Purpose**: Main application shell with navigation

**File**: `components/Layout.tsx`

```typescript
interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar Navigation */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r">
        <nav className="p-4">
          <NavLink to="/" icon={HomeIcon}>Dashboard</NavLink>
          <NavLink to="/agents" icon={CpuChipIcon}>Agents</NavLink>
          <NavLink to="/usage" icon={ChartBarIcon}>Usage</NavLink>
          <NavLink to="/billing" icon={CreditCardIcon}>Billing</NavLink>
          <NavLink to="/wallet" icon={WalletIcon}>Wallet</NavLink>
          <NavLink to="/airdrop" icon={GiftIcon}>Airdrop</NavLink>
          <NavLink to="/settings" icon={CogIcon}>Settings</NavLink>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="ml-64 p-8">
        {/* Top Bar */}
        <header className="mb-8 flex items-center justify-between">
          <h1 className="text-2xl font-bold">AgentVault</h1>
          <ConnectButton />  {/* RainbowKit */}
        </header>

        {children}
      </main>
    </div>
  );
}
```

**Features**:
- Responsive sidebar navigation
- RainbowKit wallet connection button
- Active route highlighting
- Mobile-responsive hamburger menu

#### 2. StatsCard Component

**Purpose**: Display key metrics with trends

**File**: `components/StatsCard.tsx`

```typescript
interface StatsCardProps {
  title: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  color: 'blue' | 'green' | 'purple' | 'yellow';
}

export default function StatsCard({ title, value, icon: Icon, trend, color }: StatsCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    yellow: 'bg-yellow-50 text-yellow-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>

          {trend && (
            <div className={`flex items-center mt-2 text-sm ${
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            }`}>
              {trend.isPositive ? (
                <ArrowUpIcon className="w-4 h-4 mr-1" />
              ) : (
                <ArrowDownIcon className="w-4 h-4 mr-1" />
              )}
              {trend.value}%
            </div>
          )}
        </div>

        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  );
}
```

**Usage**:
```typescript
<StatsCard
  title="Total Agents"
  value={12}
  icon={CpuChipIcon}
  trend={{ value: 15, isPositive: true }}
  color="blue"
/>
```

#### 3. TokenBalance Component

**Purpose**: Display wallet balance with real-time updates

**File**: `components/TokenBalance.tsx`

```typescript
export default function TokenBalance() {
  const { address } = useAccount();

  // ETH balance
  const { data: ethBalance } = useBalance({
    address,
    watch: true,
  });

  // AVT token balance
  const { data: avtBalance } = useBalance({
    address,
    token: AVT_TOKEN_ADDRESS,
    watch: true,
  });

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">Wallet Balance</p>
          <div className="mt-1">
            <p className="text-lg font-semibold">
              {ethBalance?.formatted} {ethBalance?.symbol}
            </p>
            <p className="text-sm text-gray-600">
              {avtBalance?.formatted} AVT
            </p>
          </div>
        </div>

        <button
          onClick={() => navigator.clipboard.writeText(address || '')}
          className="text-gray-400 hover:text-gray-600"
        >
          <ClipboardIcon className="w-5 h-5" />
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-2 truncate">
        {address}
      </p>
    </div>
  );
}
```

**Features**:
- Real-time balance updates (wagmi hooks)
- Copy address to clipboard
- Displays both ETH and AVT balances
- Responsive design

#### 4. UsageChart Component

**Purpose**: Visualize usage data with charts

**File**: `components/UsageChart.tsx`

```typescript
interface UsageChartProps {
  data?: Array<{
    date: string;
    requests: number;
    cost: number;
  }>;
  type?: 'line' | 'bar' | 'area';
}

export default function UsageChart({ data = [], type = 'line' }: UsageChartProps) {
  const ChartComponent = {
    line: LineChart,
    bar: BarChart,
    area: AreaChart,
  }[type];

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ChartComponent data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        {type === 'line' && (
          <Line type="monotone" dataKey="requests" stroke="#3b82f6" />
        )}
        {type === 'bar' && (
          <Bar dataKey="requests" fill="#3b82f6" />
        )}
        {type === 'area' && (
          <Area type="monotone" dataKey="requests" fill="#3b82f6" />
        )}
      </ChartComponent>
    </ResponsiveContainer>
  );
}
```

#### 5. RecentActivity Component

**Purpose**: Display recent user actions

**File**: `components/RecentActivity.tsx`

```typescript
interface Activity {
  id: string;
  type: 'agent_created' | 'transfer' | 'airdrop' | 'strategy';
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
}

export default function RecentActivity() {
  const { data: activities } = useQuery<Activity[]>({
    queryKey: ['recent-activity'],
    queryFn: fetchRecentActivity,
    refetchInterval: 30000, // 30 seconds
  });

  return (
    <div className="space-y-4">
      {activities?.map((activity) => (
        <div key={activity.id} className="flex items-start gap-3">
          <ActivityIcon type={activity.type} />

          <div className="flex-1">
            <p className="text-sm font-medium">{activity.description}</p>
            <p className="text-xs text-gray-500">
              {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
            </p>
          </div>

          <StatusBadge status={activity.status} />
        </div>
      ))}
    </div>
  );
}
```

### Pages

#### 1. Dashboard Page

**File**: `pages/Dashboard.tsx`

**Features**:
- 4-column stats grid (agents, usage, balance)
- Usage chart (daily/monthly)
- Recent activity feed
- Airdrop eligibility alerts
- Quick action buttons

**Layout**:
```typescript
export default function Dashboard() {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
    refetchInterval: 30000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <TokenBalance />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard {...} />
        <StatsCard {...} />
        <StatsCard {...} />
        <StatsCard {...} />
      </div>

      {/* Charts and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UsageChart />
        <RecentActivity />
      </div>

      {/* Airdrop Alert */}
      {stats?.airdropEligible && <AirdropAlert />}

      {/* Quick Actions */}
      <QuickActions />
    </div>
  );
}
```

#### 2. Agents Page

**File**: `pages/Agents.tsx`

**Features**:
- Agent list with status indicators
- Create new agent modal
- Agent details and configuration
- Wallet address display
- Activity history per agent

**Example**:
```typescript
export default function Agents() {
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  const createAgentMutation = useMutation({
    mutationFn: createAgent,
    onSuccess: () => queryClient.invalidateQueries(['agents']),
  });

  return (
    <div>
      <div className="flex justify-between mb-6">
        <h1 className="text-2xl font-bold">Agents</h1>
        <button onClick={() => setShowCreateModal(true)}>
          Create Agent
        </button>
      </div>

      <div className="grid gap-4">
        {agents?.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      <CreateAgentModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={createAgentMutation.mutate}
      />
    </div>
  );
}
```

#### 3. Airdrop Page

**File**: `pages/Airdrop.tsx`

**Features**:
- Eligibility checker
- Claim button (Web3 transaction)
- Next claim countdown
- Claim history
- Total earned display

**Implementation**:
```typescript
export default function Airdrop() {
  const { address } = useAccount();
  const { eligible, amount, claimAirdrop, isLoading } = useAirdrop(address);

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Airdrop</h1>

      <div className="bg-white rounded-lg p-6 shadow-sm">
        {eligible ? (
          <>
            <h2 className="text-xl font-semibold text-green-600">
              You're eligible for an airdrop!
            </h2>
            <p className="text-3xl font-bold mt-4">
              {formatEther(amount)} AVT
            </p>

            <button
              onClick={() => claimAirdrop?.()}
              disabled={isLoading}
              className="mt-6 w-full btn-primary"
            >
              {isLoading ? 'Claiming...' : 'Claim Airdrop'}
            </button>
          </>
        ) : (
          <>
            <h2 className="text-xl font-semibold">Not eligible yet</h2>
            <p className="text-gray-600 mt-2">
              Make at least 10 API calls to become eligible
            </p>
          </>
        )}
      </div>

      <AirdropHistory address={address} />
    </div>
  );
}
```

### Web3 Configuration

**File**: `config/web3.ts`

```typescript
import { getDefaultWallets, connectorsForWallets } from '@rainbow-me/rainbowkit';
import { configureChains, createConfig } from 'wagmi';
import { mainnet, sepolia } from 'wagmi/chains';
import { publicProvider } from 'wagmi/providers/public';

// Configure chains
const { chains, publicClient } = configureChains(
  [mainnet, sepolia],
  [publicProvider()]
);

// Wallet connectors
const projectId = process.env.REACT_APP_WALLET_CONNECT_PROJECT_ID || '';

const { wallets } = getDefaultWallets({
  appName: 'AgentVault Dashboard',
  projectId,
  chains,
});

const connectors = connectorsForWallets(wallets);

// Create wagmi config
export const wagmiConfig = createConfig({
  autoConnect: true,
  connectors,
  publicClient,
});

// RainbowKit theme
export const rainbowKitTheme = {
  lightMode: {
    accentColor: '#0ea5e9',
    accentColorForeground: 'white',
    borderRadius: 'medium',
    fontStack: 'system',
  },
};

// Contract addresses per network
export const CONTRACT_ADDRESSES = {
  AGENT_VAULT_TOKEN: {
    [mainnet.id]: '0x0000000000000000000000000000000000000000', // Deploy here
    [sepolia.id]: '0x0000000000000000000000000000000000000000', // Testnet
  },
};

export const SUPPORTED_CHAINS = [mainnet, sepolia];
```

### Custom Hooks

**Example: useAirdrop Hook**

**File**: `hooks/useAirdrop.ts`

```typescript
import { useContractRead, useContractWrite, useWaitForTransaction } from 'wagmi';
import { AVT_ABI, CONTRACT_ADDRESSES } from '../config/web3';
import { useChainId } from 'wagmi';

export function useAirdrop(userAddress: string | undefined) {
  const chainId = useChainId();
  const avtAddress = CONTRACT_ADDRESSES.AGENT_VAULT_TOKEN[chainId];

  // Read airdrop info
  const { data: airdropInfo } = useContractRead({
    address: avtAddress,
    abi: AVT_ABI,
    functionName: 'getAirdropInfo',
    args: [userAddress],
    watch: true,
    enabled: !!userAddress,
  });

  // Claim airdrop write
  const { data, write: claimAirdrop } = useContractWrite({
    address: avtAddress,
    abi: AVT_ABI,
    functionName: 'claimAirdrop',
  });

  // Wait for transaction
  const { isLoading } = useWaitForTransaction({
    hash: data?.hash,
  });

  return {
    eligible: airdropInfo?.[0] ?? false,
    amount: airdropInfo?.[1] ?? 0n,
    timeUntilNext: airdropInfo?.[2] ?? 0n,
    claimAirdrop,
    isLoading,
  };
}
```

## Backend API

### API Overview

**Base URL**: `http://localhost:8000`

**Authentication**: JWT Bearer tokens

**CORS**: Enabled for `localhost:3000`, `localhost:3001`

### Endpoints

#### Authentication

**POST `/auth/login`**

Login with email and password.

```typescript
// Request
{
  "email": "user@example.com",
  "password": "secret123"
}

// Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "wallet_address": "0x742d35Cc...",
    "token_balance": 1250.50,
    "total_usage": 15420
  }
}
```

#### Dashboard

**GET `/dashboard/stats`**

Get overview statistics.

```typescript
// Response
{
  "totalAgents": 12,
  "activeAgents": 8,
  "totalUsage": 15420,
  "monthlyUsage": 3420,
  "tokenBalance": "1,250.50",
  "airdropEligible": true,
  "nextAirdrop": "2024-02-15T10:00:00Z"
}
```

#### Agents

**GET `/agents`**

List all agents for authenticated user.

```typescript
// Response
[
  {
    "id": "1",
    "name": "Trading Bot Alpha",
    "description": "Automated ETH trading with DCA strategy",
    "wallet_address": "0x742d35Cc6cCc44C4Af2d4C8c4c4c4c4c4c4c4c4c4",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "last_active": "2024-01-15T12:30:00Z"
  }
]
```

**POST `/agents/create`**

Create a new agent.

```typescript
// Request
{
  "name": "My Trading Bot",
  "description": "DCA strategy on ETH"
}

// Response
{
  "id": "new-agent-id",
  "name": "My Trading Bot",
  "description": "DCA strategy on ETH",
  "wallet_address": "0x1234567890abcdef...",
  "status": "created"
}
```

#### Usage & Billing

**GET `/usage`**

Get usage statistics.

```typescript
// Response
{
  "total_requests": 15420,
  "total_cost": 1250.50,
  "daily_usage": [
    { "date": "2024-01-01", "requests": 120, "cost": 12.50 },
    { "date": "2024-01-02", "requests": 98, "cost": 9.80 }
  ],
  "monthly_usage": [
    { "month": "2024-01", "requests": 3420, "cost": 342.00 }
  ]
}
```

**GET `/billing/history`**

Get billing history.

```typescript
// Response
[
  {
    "id": "1",
    "amount": 25.50,
    "description": "API Usage - January 2024",
    "timestamp": "2024-01-10T00:00:00Z",
    "status": "paid"
  }
]
```

#### Wallet & Airdrop

**GET `/wallet/balance`**

Get wallet balance.

```typescript
// Response
{
  "eth_balance": "1.25",
  "token_balance": "1250.50",
  "wallet_address": "0x742d35Cc..."
}
```

**GET `/airdrop/info`**

Get airdrop information.

```typescript
// Response
{
  "eligible": true,
  "amount": 100.0,
  "next_claim": "2024-02-15T10:00:00Z",
  "total_claimed": 450.0
}
```

**POST `/airdrop/claim`**

Claim airdrop (mock - will be Web3 transaction).

```typescript
// Response
{
  "success": true,
  "amount": 100.0,
  "transaction_hash": "0x1234567890abcdef",
  "message": "Airdrop claimed successfully!"
}
```

### Authentication

**JWT Implementation**:

```python
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

**Usage in Routes**:

```python
@app.get("/agents")
async def get_agents(token_data: dict = Depends(verify_token)):
    user_id = token_data["sub"]
    # Fetch agents for user_id
    return agents
```

## Integration Guide

### Connecting Dashboard to MCP Server

**Current State**: Dashboard uses mock data

**Goal**: Integrate with AgentVault MCP server and database

#### Step 1: Shared Database

**Backend Configuration** (`dashboard/backend/.env`):
```bash
VAULTPILOT_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/agentvault
```

**Initialize MCP Components**:
```python
# dashboard/backend/main.py
from agentvault_mcp.wallet import AgentWalletManager
from agentvault_mcp.core import ContextManager
from agentvault_mcp.adapters.web3_adapter import Web3Adapter
from agentvault_mcp.db.repositories import WalletRepository, EventRepository

# Shared configuration
DATABASE_URL = os.getenv("VAULTPILOT_DATABASE_URL")
RPC_URL = os.getenv("WEB3_RPC_URL")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")

# Initialize MCP components
ctx = ContextManager()
web3_adapter = Web3Adapter(RPC_URL)
wallet_manager = AgentWalletManager(
    ctx,
    web3_adapter,
    ENCRYPT_KEY,
    database_url=DATABASE_URL
)
```

#### Step 2: Replace Mock Endpoints

**Before** (Mock):
```python
@app.post("/agents/create")
async def create_agent(name: str, token_data: dict = Depends(verify_token)):
    return {
        "id": "mock-id",
        "name": name,
        "wallet_address": "0x1234...",
    }
```

**After** (Real):
```python
@app.post("/agents/create")
async def create_agent(name: str, token_data: dict = Depends(verify_token)):
    user_id = token_data["sub"]
    agent_id = f"{user_id}_{name}"

    # Call MCP wallet manager
    address = await wallet_manager.spin_up_wallet(agent_id)

    return {
        "id": agent_id,
        "name": name,
        "wallet_address": address,
        "status": "created"
    }
```

**Get Balance**:
```python
@app.get("/agents/{agent_id}/balance")
async def get_balance(agent_id: str, token_data: dict = Depends(verify_token)):
    balance_eth = await wallet_manager.query_balance(agent_id)
    return {"balance_eth": balance_eth}
```

#### Step 3: Add Web3 Contract Calls

**Smart Contract Integration**:
```python
from web3 import Web3
from eth_account import Account

# Load AVT contract
web3 = Web3(Web3.HTTPProvider(RPC_URL))
avt_contract = web3.eth.contract(
    address=os.getenv("AVT_TOKEN_ADDRESS"),
    abi=AVT_ABI  # Load from file
)

@app.get("/airdrop/info")
async def get_airdrop_info(token_data: dict = Depends(verify_token)):
    user_address = token_data["wallet_address"]

    # Call smart contract
    eligible, amount, time_until = avt_contract.functions.getAirdropInfo(
        user_address
    ).call()

    return {
        "eligible": eligible,
        "amount": Web3.from_wei(amount, 'ether'),
        "seconds_until_next": time_until
    }
```

### Deployment

#### Development

**Frontend**:
```bash
cd dashboard
npm install
npm start  # http://localhost:3000
```

**Backend**:
```bash
cd dashboard/backend
pip install -r requirements.txt
python main.py  # http://localhost:8000
```

#### Production

**Frontend (Vercel/Netlify)**:
```bash
npm run build
# Deploy dist/ folder
```

**Backend (Docker)**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment Variables**:
```bash
# .env.production
REACT_APP_API_URL=https://api.agentvault.com
REACT_APP_WALLET_CONNECT_PROJECT_ID=your-project-id
REACT_APP_CHAIN_ID=1

# Backend
JWT_SECRET_KEY=your-super-secret-key
VAULTPILOT_DATABASE_URL=postgresql://...
WEB3_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/...
AVT_TOKEN_ADDRESS=0x...
ENCRYPT_KEY=...
```

## Development Guide

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/agentvault-mcp.git
cd agentvault-mcp/dashboard

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# Start development server
npm start
```

### Code Style

**TypeScript**:
```typescript
// Use functional components with hooks
export default function MyComponent() {
  const [state, setState] = useState();

  return <div>...</div>;
}

// Type all props
interface MyComponentProps {
  title: string;
  count?: number;
}

// Use const for functions
const handleClick = () => {
  // ...
};
```

**Tailwind CSS**:
```typescript
// Use utility classes
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">

// Responsive design
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">

// Dark mode (future)
<div className="bg-white dark:bg-gray-800">
```

### Testing

**Run Tests**:
```bash
npm test
npm test -- --coverage
```

**Example Test**:
```typescript
import { render, screen } from '@testing-library/react';
import StatsCard from './StatsCard';

test('renders stats card with correct value', () => {
  render(
    <StatsCard
      title="Total Agents"
      value={12}
      icon={CpuChipIcon}
      color="blue"
    />
  );

  expect(screen.getByText('Total Agents')).toBeInTheDocument();
  expect(screen.getByText('12')).toBeInTheDocument();
});
```

### Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and add tests
4. Run tests: `npm test`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

---

## Roadmap

### v1.0 (Current)
- ✅ Modern React dashboard
- ✅ Token-based billing system
- ✅ Wallet integration (RainbowKit)
- ✅ Usage analytics
- ✅ Airdrop system UI

### v1.1 (Next)
- 🔄 MCP server integration
- 🔄 Smart contract integration
- 🔄 Real-time notifications
- 🔄 Advanced analytics
- 🔄 Mobile responsive improvements

### v2.0 (Future)
- 🔄 Mobile app (React Native)
- 🔄 Multi-language support
- 🔄 DeFi integration UI
- 🔄 NFT marketplace
- 🔄 Social features
- 🔄 Enterprise features

---

For MCP server documentation, see [../README.md](../README.md).
For smart contract documentation, see [token-economics.md](token-economics.md).
For architecture details, see [architecture.md](architecture.md).
