# 🚀 AgentVault Dashboard

A modern, crypto-powered dashboard for managing AI agents with token-based billing and usage analytics. Built with React, TypeScript, and inspired by leading AI platforms like OpenAI and Claude.

## ✨ Features

### 🎯 **Core Functionality**
- **Modern React Dashboard** - Clean, responsive UI with real-time updates
- **Token-Based Economy** - Pay for agent services using AVT tokens
- **Wallet Integration** - Connect your wallet and manage token balances
- **Agent Management** - Create, monitor, and manage AI agents
- **Usage Analytics** - Real-time usage statistics and cost tracking
- **Airdrop System** - Earn tokens by actively using the platform

### 💰 **Token Economy**
- **AVT Token** - Native ERC-20 token for the AgentVault ecosystem
- **Usage-Based Billing** - Pay per API call with transparent pricing
- **Airdrop Rewards** - Active users receive token rewards
- **Token Balance** - Real-time balance tracking and transaction history

### 📊 **Analytics & Monitoring**
- **Usage Charts** - Visual representation of API usage over time
- **Cost Analysis** - Track spending and optimize agent usage
- **Real-time Updates** - Live data with automatic refresh
- **Performance Metrics** - Monitor agent efficiency and success rates

### 🔐 **Security & Authentication**
- **JWT Authentication** - Secure API access with token-based auth
- **Wallet Connection** - Connect with MetaMask, WalletConnect, etc.
- **Role-Based Access** - Different permission levels for users
- **Audit Logging** - Comprehensive activity tracking

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend│◄──►│  FastAPI Backend│◄──►│   Smart Contracts│
│                 │    │                 │    │                 │
│ • Dashboard     │    │ • REST API      │    │ • AVT Token     │
│ • Charts        │    │ • Authentication│    │ • Airdrop Logic │
│ • Wallet UI     │    │ • Rate Limiting │    │ • Usage Tracking│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌─────────────────┐
│   AgentVault MCP│    │   Blockchain    │
│                 │    │                 │
│ • Core Engine   │    │ • Ethereum      │
│ • Wallet Manager│    │ • Smart Contracts│
│ • Strategy Engine│   │ • Token Transfers│
└─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+ and pip
- **MetaMask** or other Web3 wallet
- **Git**

### 1. Install Frontend Dependencies

```bash
cd dashboard
npm install
```

### 2. Install Backend Dependencies

```bash
cd dashboard/backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create `.env` files for both frontend and backend:

**Frontend (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WALLET_CONNECT_PROJECT_ID=your-project-id
```

**Backend (.env):**
```bash
JWT_SECRET_KEY=your-super-secret-jwt-key
DATABASE_URL=sqlite+aiosqlite:///agentvault.db
```

### 4. Start the Backend API

```bash
cd dashboard/backend
python main.py
```

### 5. Start the Frontend Dashboard

```bash
cd dashboard
npm start
```

### 6. Deploy Smart Contracts (Optional)

```bash
# Deploy to testnet
npx hardhat run scripts/deploy.js --network sepolia

# Deploy to mainnet
npx hardhat run scripts/deploy.js --network mainnet
```

## 📁 Project Structure

```
dashboard/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Layout.tsx      # Main layout with navigation
│   │   ├── StatsCard.tsx   # Statistics display cards
│   │   ├── TokenBalance.tsx # Wallet balance component
│   │   ├── UsageChart.tsx  # Usage analytics charts
│   │   └── RecentActivity.tsx # Activity feed
│   ├── pages/              # Main application pages
│   │   ├── Dashboard.tsx   # Main dashboard
│   │   ├── Agents.tsx      # Agent management
│   │   ├── Usage.tsx       # Usage analytics
│   │   ├── Billing.tsx     # Billing and payments
│   │   ├── Wallet.tsx      # Wallet management
│   │   ├── Airdrop.tsx     # Airdrop claims
│   │   └── Settings.tsx    # User settings
│   ├── config/             # Configuration files
│   │   └── web3.ts         # Web3 and wallet config
│   ├── hooks/              # Custom React hooks
│   └── utils/              # Utility functions
├── backend/                # FastAPI backend
│   ├── main.py            # Main API application
│   └── requirements.txt   # Python dependencies
└── contracts/             # Smart contracts
    └── AgentVaultToken.sol # AVT token contract
```

## 🔧 Configuration

### Frontend Configuration

**Environment Variables:**
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WALLET_CONNECT_PROJECT_ID=your-walletconnect-id
REACT_APP_CHAIN_ID=1  # 1 for mainnet, 11155111 for sepolia
```

**Supported Networks:**
- Ethereum Mainnet
- Sepolia Testnet
- Local development networks

### Backend Configuration

**Environment Variables:**
```bash
# Security
JWT_SECRET_KEY=your-super-secret-key
API_SECRET_KEY=your-api-secret

# Database
DATABASE_URL=sqlite+aiosqlite:///agentvault.db

# Blockchain
WEB3_RPC_URL=https://ethereum-sepolia.publicnode.com
CONTRACT_ADDRESS=0x1234...  # Deployed AVT token address

# External Services
REDIS_URL=redis://localhost:6379  # For caching
```

## 🎨 UI Components

### Dashboard Layout
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Modern Styling** - Clean, professional interface with Tailwind CSS
- **Dark Mode Support** - Toggle between light and dark themes
- **Accessibility** - WCAG compliant with keyboard navigation

### Key Components

#### StatsCard
```tsx
<StatsCard
  title="Total Agents"
  value={12}
  icon={CpuChipIcon}
  trend={{ value: 15, isPositive: true }}
  color="blue"
/>
```

#### UsageChart
```tsx
<UsageChart
  data={usageData}
  type="line" // or "bar", "area"
/>
```

#### TokenBalance
```tsx
<TokenBalance
  showWalletAddress={true}
  refreshInterval={30000}
/>
```

## 🔌 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/me` - Get current user info

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics
- `GET /dashboard/recent-activity` - Get recent user activity

### Agents
- `GET /agents` - List user's agents
- `POST /agents` - Create new agent
- `PUT /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

### Usage & Billing
- `GET /usage` - Get usage statistics
- `GET /billing/history` - Get billing history
- `GET /billing/invoices` - Get invoices

### Token & Airdrop
- `GET /token/balance` - Get token balance
- `POST /airdrop/claim` - Claim airdrop
- `GET /airdrop/info` - Get airdrop information

### Wallet
- `GET /wallet/transactions` - Get transaction history
- `POST /wallet/transfer` - Transfer tokens

## 💰 Token Economics

### AVT Token
- **Symbol**: AVT
- **Decimals**: 18
- **Total Supply**: 1,000,000,000 AVT
- **Contract**: ERC-20 compliant

### Pricing Model
- **Base Rate**: 0.01 AVT per API call
- **Volume Discounts**: Reduced rates for high-volume users
- **Subscription Tiers**: Different pricing for different user tiers

### Airdrop System
- **Eligibility**: 10+ API calls per month
- **Base Reward**: 100 AVT for active users
- **Bonus Rewards**: Additional tokens for high usage
- **Claim Interval**: 30 days

## 🔐 Security Features

### Authentication
- **JWT Tokens** - Secure, stateless authentication
- **Password Hashing** - bcrypt with salt rounds
- **Rate Limiting** - Prevent brute force attacks

### API Security
- **CORS Protection** - Configurable origin policies
- **Input Validation** - Pydantic models for all inputs
- **SQL Injection Prevention** - Parameterized queries

### Wallet Security
- **Private Key Protection** - Never stored in plain text
- **Transaction Signing** - Secure signing with user approval
- **Address Validation** - Checksum validation for all addresses

## 📊 Analytics & Monitoring

### Usage Tracking
- **Real-time Metrics** - Live usage and cost tracking
- **Historical Data** - 30-day rolling history
- **Performance Monitoring** - Agent success rates and latency

### Business Intelligence
- **Revenue Analytics** - Track earnings and user spending
- **User Behavior** - Understand usage patterns
- **System Health** - Monitor API performance and uptime

## 🚀 Deployment

### Frontend Deployment
```bash
# Build for production
npm run build

# Deploy to Vercel, Netlify, or your preferred platform
vercel --prod
```

### Backend Deployment
```bash
# Using Docker
docker build -t agentvault-api .
docker run -p 8000:8000 agentvault-api

# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Smart Contract Deployment
```bash
# Deploy to testnet
npx hardhat run scripts/deploy.js --network sepolia

# Verify contract
npx hardhat verify --network sepolia <contract-address>
```

## 🧪 Testing

### Frontend Testing
```bash
# Run unit tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run E2E tests
npm run test:e2e
```

### Backend Testing
```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run integration tests
pytest tests/integration/
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and add tests
4. **Run the test suite**: `npm test && pytest`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.agentvault.com](https://docs.agentvault.com)
- **Discord**: [discord.agentvault.com](https://discord.agentvault.com)
- **GitHub Issues**: [github.com/agentvault/dashboard/issues](https://github.com/agentvault/dashboard/issues)

## 🔮 Roadmap

### v1.0 (Current)
- ✅ Modern React dashboard
- ✅ Token-based billing system
- ✅ Wallet integration
- ✅ Usage analytics
- ✅ Airdrop system

### v1.1 (Next)
- 🔄 Mobile app development
- 🔄 Advanced analytics
- 🔄 Multi-language support
- 🔄 API rate limiting

### v2.0 (Future)
- 🔄 DeFi integration
- 🔄 NFT marketplace
- 🔄 Social features
- 🔄 Enterprise features

---

**AgentVault Dashboard** - The future of AI agent management is here! 🚀