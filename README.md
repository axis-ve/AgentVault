# AgentVault MCP

This is a **truly autonomous** Model Context Protocol (MCP) plugin that enables AI agents to independently manage Ethereum wallets without requiring any user-provided API keys or manual wallet management. The agent generates wallets, finds funding sources, and executes transactions autonomously.

## What Makes This Different?

**❌ Old Way (What Most MCP Plugins Do):**
- Require users to provide API keys
- Force manual wallet creation and funding
- User manages all crypto operations
- Not truly autonomous

**✅ New Way (This Plugin):**
- Agent generates its own wallets automatically
- Agent finds and suggests funding options (faucets, exchanges)
- Agent handles all crypto operations independently
- User only provides initial funding approval
- **Zero API keys required from user**

## How It Works - The Autonomous Flow

### Step 1: Agent Generates Wallet
```
User: "I want to start trading crypto"
AI: "I'll create a secure wallet for you."
  ↓
Agent calls: spin_up_wallet("trading_agent")
  ↓
✅ Wallet created: 0x1234...abcd
✅ Funding options provided automatically
✅ Agent ready to operate
```

### Step 2: Agent Finds Funding
```
AI: "Your wallet is empty. Here are funding options:"
  ↓
Agent calls: get_funding_options("trading_agent")
  ↓
📋 Faucet: https://sepoliafaucet.com/ (Free testnet ETH)
📋 Exchange: Coinbase, Binance (Real ETH)
✅ Agent suggests best option based on context
```

### Step 3: Agent Monitors and Acts
```
AI: "I see you have 0.05 ETH now. Ready to trade?"
  ↓
Agent calls: query_balance("trading_agent")
  ↓
💰 Balance: 0.05 ETH
📊 Health: Good
🎯 Actions: Suggest trading opportunities
```

### Step 4: Agent Executes Transactions
```
User: "Buy some tokens"
AI: "Executing autonomous transaction..."
  ↓
Agent calls: execute_transfer("trading_agent", "0xTokenContract", 0.01)
  ↓
✅ Transaction signed and submitted
✅ Confirmed on blockchain
✅ Balance updated automatically
```

## Zero Setup Required

**Before (Traditional):**
```bash
# User must:
1. Get OpenAI API key ($)
2. Get Infura RPC key
3. Generate encryption key
4. Create wallet manually
5. Fund wallet manually
6. Provide all keys to agent
```

**After (Autonomous):**
```bash
# User just runs:
python -m agentvault_mcp.server
# or, after installing the package: agentvault-mcp

# Agent handles everything else autonomously!
```

## Available Autonomous Tools

| Tool | Purpose | Agent Action |
|------|---------|--------------|
| `spin_up_wallet` | Create secure wallet | Generates HD wallet + suggests funding |
| `query_balance` | Check ETH balance | Fetches balance + suggests actions |
| `execute_transfer` | Send ETH | Signs and submits transaction |
| `get_funding_options` | Find funding sources | Provides faucets + exchanges |
| `autonomous_action` | Smart decision making | Analyzes context and acts |

## Security Architecture

```
🔐 Private keys: Encrypted with auto-generated Fernet key
🌐 RPC: Uses public endpoints (no API keys needed)
⚡ Transactions: Signed locally, never exposed
📊 Monitoring: All actions logged with structured logging
🛡️ Validation: Addresses and amounts validated before execution
```

## Real-World Usage Examples

### Example 1: New User Onboarding
```
User: "I'm new to crypto, help me get started"
AI: "I'll set up everything for you autonomously"

1. Creates wallet: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e
2. Provides faucet link for free testnet ETH
3. Monitors balance until funded
4. Suggests next steps based on balance
```

### Example 2: Autonomous Trading
```
User: "Start automated trading with 0.1 ETH"
AI: "I'll manage your trading autonomously"

1. Checks current balance
2. Calculates safe trade amounts
3. Executes trades based on market conditions
4. Monitors profits/losses
5. Adjusts strategy automatically
```

### Example 3: Portfolio Management
```
User: "Manage my crypto portfolio"
AI: "I'll handle your portfolio autonomously"

1. Tracks all wallet balances
2. Monitors market conditions
3. Suggests rebalancing trades
4. Executes approved transactions
5. Provides performance reports
```

## Installation & Usage

### Quick Start (2 minutes)
```bash
# 1. Clone and setup
git clone <repo>
cd autonomous-wallet-mcp
pip install -r requirements.txt

# 2. Run autonomous server
python -m agentvault_mcp.server

# 3. Connect your AI agent (Claude, etc.)
# Agent automatically discovers all wallet tools
```

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
