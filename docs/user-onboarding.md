# AgentVault MCP User Onboarding Guide

## 🎯 For First-Time Users

AgentVault MCP enables AI agents to autonomously manage Ethereum wallets through the Model Context Protocol. This guide helps you get started quickly.

## Prerequisites

- Python 3.10+ installed
- Basic familiarity with command line
- (Optional) Claude Desktop, Cursor IDE, or Claude Code for MCP integration

## Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/axis-ve/AgentVault.git
cd AgentVault

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Apply database migrations (uses VAULTPILOT_DATABASE_URL or defaults to SQLite)
python -m agentvault_mcp.db.cli upgrade
```

If you previously used the legacy JSON stores, import them after migrating:

```bash
python -m agentvault_mcp.db.import_legacy \
  --wallet-store agentvault_store.json \
  --strategy-store agentvault_strategies.json
```

## Step 2: Basic Testing

Test that everything works without any configuration:

```bash
# Test CLI (uses public testnet RPC)
agentvault --help
agentvault create-wallet test-agent
agentvault balance test-agent

# Test MCP server
python -m agentvault_mcp.server
# Press Ctrl+C to stop
```

## Step 3: MCP Client Integration

### Option A: Claude Desktop

1. Locate your Claude Desktop config file:
   - **macOS**: `~/.config/claude-desktop/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add AgentVault to your config:
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

3. Restart Claude Desktop

4. Test by asking Claude: "Can you create a wallet for agent1?"

### Option B: Cursor IDE

1. Open Cursor IDE settings
2. Navigate to MCP configuration
3. Add server configuration:
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

### Option C: Claude Code

1. In your project root, create `.claude/settings.json`:
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

## Step 4: First Agent Wallet

Once MCP is configured, try these workflows:

### Via MCP Client (Claude/Cursor)
```
"Create a wallet for my trading agent called 'trader1'"
"Check the balance of trader1"
"Generate a tip jar page for trader1"
```

### Via CLI
```bash
agentvault create-wallet trader1
agentvault balance trader1
agentvault tip-jar-page trader1 --amount 0.01 --out tipjar.html
```

## Step 5: Advanced Configuration (Optional)

For production use, create `.env` file:

```bash
# Copy example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

Key environment variables:
- `WEB3_RPC_URL`: Your Ethereum RPC endpoint
- `ALCHEMY_API_KEY` or `ALCHEMY_HTTP_URL`/`ALCHEMY_WS_URL`: Preferred Alchemy config
- `OPENAI_API_KEY`: For LLM integration
- `ENCRYPT_KEY`: For wallet encryption (auto-generated if not set)
  
Optional UI extra (for QR/HTML):
```bash
pip install 'agentvault-mcp[ui]'
```

## Available MCP Tools

Your AI agent now has access to 21 tools:

**Core Wallet Operations:**
- `spin_up_wallet(agent_id)` - Create new wallet
- `query_balance(agent_id)` - Check ETH balance
- `execute_transfer(agent_id, to, amount)` - Send ETH
- `simulate_transfer(agent_id, to, amount)` - Dry run transfers

**Strategy Tools:**
- `send_when_gas_below(agent_id, to, amount, max_gwei)` - Conditional sends
- `dca_once(agent_id, to, amount)` - Dollar cost averaging
- `create_strategy_dca(...)` - Persistent DCA strategies

**Utility Tools:**
- `export_wallet_keystore(agent_id, passphrase)` - Backup wallets
- `request_faucet_funds(agent_id)` - Get testnet ETH
- `generate_tipjar_page(agent_id)` - Create tip jar HTML
- `generate_dashboard_page()` - Create wallet dashboard

## Common Workflows

### 1. Basic Transfer
```python
# Via MCP tools
address = await agent.call_tool("spin_up_wallet", {"agent_id": "sender"})
balance = await agent.call_tool("query_balance", {"agent_id": "sender"})
result = await agent.call_tool("execute_transfer", {
    "agent_id": "sender",
    "to_address": "0x1234...5678",
    "amount_eth": 0.001
})
```

### 2. Conditional Strategy
```python
# Send when gas is below 20 gwei
result = await agent.call_tool("send_when_gas_below", {
    "agent_id": "trader",
    "to_address": "0x1234...5678",
    "amount_eth": 0.01,
    "max_base_fee_gwei": 20.0
})
```

### 3. UI Generation
```python
# Create tip jar with QR code via MCP tool
html = await agent.call_tool("generate_tipjar_page", {
    "agent_id": "creator",
    "amount_eth": 0.005
})
```

### 4. Inspect Network State
```python
status = await agent.call_tool("provider_status", {})
print(status["chain_id"], status["latest_block_number"], status["base_fee_per_gas_gwei"])

contract = await agent.call_tool("inspect_contract", {
    "address": "0xUniversalRouter..."
})
if contract["is_contract"]:
    print(contract.get("erc20_metadata"))
```

## Security Notes

- **Private keys** are encrypted with Fernet and never stored in plaintext
- **Spend limits** can be configured via `AGENTVAULT_MAX_TX_ETH`
- **Confirmation codes** required for high-value transfers
- **Testnet first** - always test on Sepolia before mainnet

## Troubleshooting

### Common Issues

**"Command not found: agentvault"**
- Ensure you activated the virtual environment: `source .venv/bin/activate`
- Reinstall: `pip install -e .`

**"Connection failed" errors**
- Check your `WEB3_RPC_URL` is accessible
- Try the default public RPC: `https://ethereum-sepolia.publicnode.com`

**MCP server not detected**
- Verify the command path in your MCP client config
- Check that `python -m agentvault_mcp.server` runs without errors

### Getting Help

1. Check the [main README](../README.md) for detailed documentation
2. Run tests to verify your setup: `pytest -v`
3. Review example workflows in the `examples/` directory
4. Open GitHub issues for bugs or feature requests

## Next Steps

Once you're comfortable with basic operations:

1. **Explore strategies** - Set up DCA or conditional transfers
2. **Build UI** - Generate tip jars and dashboards for your projects
3. **Integrate with agents** - Use the 21 MCP tools in your AI workflows
4. **Go production** - Configure mainnet RPCs and security settings

The AgentVault MCP architecture makes it easy to build sophisticated autonomous crypto agents while maintaining security and user control.
