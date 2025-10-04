# 🚀 AgentVault MCP - Quick Start Guide

Get AgentVault running locally in **5 minutes**!

## Prerequisites

Before you begin, ensure you have:

- ✅ **Python 3.10+** installed
- ✅ **Node.js 18+** and npm installed
- ✅ **Git** installed
- ✅ **Terminal** access

Check versions:
```bash
python3 --version   # Should be 3.10 or higher
node --version      # Should be v18 or higher
npm --version       # Should be 8 or higher
```

## Step 1: Clone & Navigate

```bash
cd ~/Desktop/Brojects/MCP
# Or wherever your project is located
```

## Step 2: Generate Encryption Key

**IMPORTANT**: AgentVault needs an encryption key to secure wallet private keys.

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output (looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4==`)

## Step 3: Configure Environment

```bash
# Create .env file from template
cp .env.local .env

# Edit .env file
nano .env  # or use any text editor
```

**Find this line**:
```bash
ENCRYPT_KEY=
```

**Paste your generated key**:
```bash
ENCRYPT_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4==
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter` in nano).

**Optional**: Review other settings in `.env`:
- `WEB3_RPC_URL`: Already set to Sepolia testnet (free)
- `AGENTVAULT_MAX_TX_ETH`: Max transaction without confirmation (0.1 ETH)
- `JWT_SECRET_KEY`: Already set for local dev

## Step 4: Start AgentVault

```bash
./start-local.sh
```

This script will:
1. ✅ Create virtual environment
2. ✅ Install all Python dependencies
3. ✅ Install dashboard dependencies
4. ✅ Run database migrations
5. ✅ Start backend API (http://localhost:8000)
6. ✅ Start frontend dashboard (http://localhost:3000)

**Wait ~30 seconds** for the frontend to compile.

## Step 5: Access Dashboard

Open your browser to: **http://localhost:3000**

### Login Credentials

```
Email:    demo@agentvault.com
Password: demo123
```

## Step 6: Create Your First Agent

1. Click **"Agents"** in the sidebar
2. Click **"Create Agent"** button
3. Enter:
   - **Name**: `my-first-bot`
   - **Description**: `My first AI agent wallet`
4. Click **"Create"**

🎉 **Success!** You now have a wallet with a unique Ethereum address!

## Step 7: Get Testnet ETH (Optional)

To test transactions, you need testnet ETH:

### Option 1: Sepolia Faucet
1. Copy your agent's wallet address from the dashboard
2. Visit: https://sepoliafaucet.com/
3. Paste address and request ETH

### Option 2: Use CLI

```bash
# Activate virtual environment
source .venv/bin/activate

# Check balance
agentvault balance my-first-bot

# List all wallets
agentvault list-wallets
```

## What's Running?

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:3000 | React web interface |
| **Backend API** | http://localhost:8000 | FastAPI server |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/health | Service status |

## View Logs

```bash
# Backend logs
tail -f .pids/backend.log

# Frontend logs
tail -f .pids/frontend.log
```

## Stop All Services

```bash
./stop-local.sh
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Kill process on port 8000 (backend)
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

### Database Errors

```bash
# Reset database
rm agentvault.db
python -m agentvault_mcp.db.cli upgrade
```

### Module Not Found

```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -e '.[ui]'
cd dashboard/backend && pip install -r requirements.txt
```

### Frontend Won't Start

```bash
cd dashboard
rm -rf node_modules package-lock.json
npm install
npm start
```

## Next Steps

### 1. Explore the Dashboard

- **Dashboard**: View statistics and recent activity
- **Agents**: Manage agent wallets
- **Usage**: View API usage analytics
- **Strategies**: Create automated DCA strategies
- **Wallet**: View balances and transactions
- **Settings**: Configure your profile

### 2. Try CLI Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Create a new wallet
agentvault create-wallet trading-bot

# Check balance
agentvault balance trading-bot

# Send ETH (on testnet)
agentvault send trading-bot 0x742d35Cc6634Db53853B749t35... 0.01

# Create a DCA strategy
agentvault strategy create my-dca \
  --agent trading-bot \
  --to 0xRecipientAddress \
  --amount 0.01 \
  --interval 86400

# Start the strategy
agentvault strategy start my-dca

# Execute strategy (if due)
agentvault strategy tick my-dca
```

### 3. Use MCP with Claude Desktop

Edit `~/.config/claude-desktop/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"],
      "env": {
        "WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com",
        "ENCRYPT_KEY": "YOUR_KEY_HERE",
        "VAULTPILOT_DATABASE_URL": "sqlite+aiosqlite:///PATH/TO/agentvault.db"
      }
    }
  }
}
```

Restart Claude Desktop, then try:
```
You: Create a wallet for my trading bot
Claude: [Creates wallet using MCP tools]

You: What's my balance?
Claude: [Queries balance using MCP tools]
```

### 4. Deploy Smart Contract (Advanced)

See [docs/token-economics.md](docs/token-economics.md#deployment) for deploying the AVT token contract.

### 5. Integrate Everything

See [docs/dashboard.md](docs/dashboard.md#integration-guide) for connecting:
- Dashboard ↔ MCP Server (already done!)
- Dashboard ↔ Smart Contracts
- Smart Contract ↔ Backend API

## Production Deployment

For production deployment with Docker, see:
- [README.md#deployment](README.md#deployment)
- [docs/architecture.md](docs/architecture.md)

## Support

- 📚 **Docs**: [docs/](docs/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/axis-ve/AgentVault/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/axis-ve/AgentVault/discussions)

---

## Common Use Cases

### 1. Create Multiple Agents

```bash
agentvault create-wallet bot-1
agentvault create-wallet bot-2
agentvault create-wallet bot-3

# List all
agentvault list-wallets
```

### 2. Send Test Transaction

```bash
# Send 0.001 ETH from bot-1 to bot-2
agentvault send bot-1 <bot-2-address> 0.001
```

### 3. Monitor Gas Prices

```bash
# Check current network status
curl http://localhost:8000/health
```

### 4. Automate with Cron

```bash
# Edit crontab
crontab -e

# Add line to tick strategies every hour
0 * * * * cd /path/to/MCP && source .venv/bin/activate && agentvault strategy tick my-dca
```

---

## Architecture Overview

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Browser    │─────▶│  Frontend   │      │   Claude    │
│             │      │ (React)     │      │  Desktop    │
└─────────────┘      └──────┬──────┘      └──────┬──────┘
                            │                    │
                    REST API│              MCP   │Protocol
                            ▼                    ▼
                     ┌──────────────────────────────┐
                     │    Backend API + MCP Server  │
                     │  (FastAPI + AgentVault MCP)  │
                     └────────────┬─────────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
         ┌──────▼──────┐   ┌──────▼──────┐   ┌─────▼─────┐
         │  Database   │   │  Ethereum   │   │   Policy  │
         │  (SQLite)   │   │  (Sepolia)  │   │   Engine  │
         └─────────────┘   └─────────────┘   └───────────┘
```

---

**Congratulations!** 🎉 You now have a fully functional AgentVault MCP installation running locally!
