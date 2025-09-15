# MCP Integration Examples

## Overview

AgentVault MCP provides 21 tools for autonomous wallet management. This guide shows practical integration examples for different MCP clients.

## Claude Desktop Integration

### Configuration
File: `~/.config/claude-desktop/claude_desktop_config.json` (macOS)
```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"],
      "env": {
        "WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com",
        "OPENAI_API_KEY": "sk-your-key-here",
        "AGENTVAULT_MAX_TX_ETH": "0.1"
      }
    }
  }
}
```

### Example Prompts
```
"Create a wallet for my trading bot called 'dca-bot' and check its balance"

"Set up a DCA strategy to send 0.001 ETH to 0x1234...5678 every hour when gas is below 20 gwei"

"Generate a tip jar page for my creator wallet with a 0.005 ETH suggested amount"

"Export the keystore for my agent wallet using password 'secure123'"
```

## Cursor IDE Integration

### Configuration
Add to Cursor's MCP settings:
```json
{
  "mcp": {
    "servers": {
      "agentvault": {
        "command": "agentvault-mcp",
        "args": [],
        "env": {
          "WEB3_RPC_URL": "https://eth-sepolia.g.alchemy.com/v2/your-key",
          "ENCRYPT_KEY": "your-base64-fernet-key"
        }
      }
    }
  }
}
```

### Code Assistant Integration
```typescript
// In your TypeScript project, let Cursor know about available tools
interface AgentVaultTools {
  spin_up_wallet(agent_id: string): Promise<string>;
  query_balance(agent_id: string): Promise<number>;
  execute_transfer(agent_id: string, to: string, amount: number): Promise<string>;
  simulate_transfer(agent_id: string, to: string, amount: number): Promise<object>;
  generate_tipjar_page(agent_id: string, amount?: number): Promise<string>;
}

// Ask Cursor: "Use the AgentVault MCP tools to create a wallet manager component"
```

## Claude Code Integration

### Configuration
File: `.claude/settings.json` in your project root:
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

### Development Workflow
```bash
# In Claude Code terminal
"Create a new agent wallet and fund it from testnet faucet"
"Simulate a transfer to check gas costs before sending"
"Build a dashboard showing all my agent wallets and their strategies"
```

## Custom MCP Client Integration

### Python Client Example
```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "agentvault_mcp.server"],
        env={"WEB3_RPC_URL": "https://ethereum-sepolia.publicnode.com"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # Create wallet
            result = await session.call_tool("spin_up_wallet", {"agent_id": "my-bot"})
            wallet_address = result.content[0].text
            print(f"Created wallet: {wallet_address}")

            # Check balance
            balance_result = await session.call_tool("query_balance", {"agent_id": "my-bot"})
            balance = float(balance_result.content[0].text)
            print(f"Balance: {balance} ETH")

            # Simulate transfer
            sim_result = await session.call_tool("simulate_transfer", {
                "agent_id": "my-bot",
                "to_address": "0x1234567890123456789012345678901234567890",
                "amount_eth": 0.001
            })
            print(f"Simulation: {sim_result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript/Node.js Client Example
```javascript
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');

async function createAgentWallet() {
    const transport = new StdioClientTransport({
        command: 'python',
        args: ['-m', 'agentvault_mcp.server'],
        env: {
            'WEB3_RPC_URL': 'https://ethereum-sepolia.publicnode.com'
        }
    });

    const client = new Client(
        { name: "wallet-manager", version: "1.0.0" },
        { capabilities: {} }
    );

    await client.connect(transport);

    // Create wallet
    const walletResult = await client.request(
        { method: "tools/call" },
        {
            name: "spin_up_wallet",
            arguments: { agent_id: "trading-bot" }
        }
    );

    console.log('Wallet created:', walletResult.content[0].text);

    // Generate tip jar
    const tipjarResult = await client.request(
        { method: "tools/call" },
        {
            name: "generate_tipjar_page",
            arguments: {
                agent_id: "trading-bot",
                amount_eth: 0.005
            }
        }
    );

    console.log('Tip jar HTML generated');
    await client.close();
}

createAgentWallet().catch(console.error);
```

## Advanced Integration Patterns

### 1. Multi-Agent Coordination
```python
# Create multiple specialized agents
agents = ["trader", "collector", "distributor"]
for agent_id in agents:
    await session.call_tool("spin_up_wallet", {"agent_id": agent_id})

# Trader executes DCA strategy
await session.call_tool("create_strategy_dca", {
    "label": "btc-dca",
    "agent_id": "trader",
    "to_address": "0xBTC...",
    "amount_eth": 0.01,
    "interval_seconds": 3600
})

# Collector gathers tips
tip_addresses = ["0xCreator1...", "0xCreator2..."]
await session.call_tool("micro_tip_equal", {
    "agent_id": "collector",
    "addresses": tip_addresses,
    "total_amount_eth": 0.1
})
```

### 2. Conditional Execution
```python
# Smart gas optimization
current_gas = await session.call_tool("query_current_gas", {})
if current_gas["base_fee_gwei"] < 15:
    await session.call_tool("execute_transfer", {
        "agent_id": "trader",
        "to_address": "0xTarget...",
        "amount_eth": 0.05
    })
else:
    await session.call_tool("send_when_gas_below", {
        "agent_id": "trader",
        "to_address": "0xTarget...",
        "amount_eth": 0.05,
        "max_base_fee_gwei": 15.0
    })
```

### 3. UI Generation Pipeline
```python
# Generate complete UI suite
dashboard_html = await session.call_tool("generate_dashboard_page", {})
tipjar_html = await session.call_tool("generate_tipjar_page", {
    "agent_id": "creator",
    "amount_eth": 0.01
})

# Save to files
with open("dashboard.html", "w") as f:
    f.write(dashboard_html.content[0].text)
with open("tipjar.html", "w") as f:
    f.write(tipjar_html.content[0].text)
```

## Environment Configuration

### Production Setup
```bash
# .env file for production
WEB3_RPC_URL=https://mainnet.infura.io/v3/your-project-id
WEB3_RPC_BACKUP_URL=https://eth-mainnet.alchemyapi.io/v2/your-key
OPENAI_API_KEY=sk-your-openai-key
ENCRYPT_KEY=your-base64-fernet-key
AGENTVAULT_MAX_TX_ETH=1.0
AGENTVAULT_TX_CONFIRM_CODE=production-secret
AGENTVAULT_STORE=/secure/path/to/wallets.json
LOG_LEVEL=INFO
```

### Development Setup
```bash
# .env file for development
WEB3_RPC_URL=https://ethereum-sepolia.publicnode.com
AGENTVAULT_FAUCET_URL=https://sepoliafaucet.com/api/request
AGENTVAULT_MAX_TX_ETH=0.1
LOG_LEVEL=DEBUG
```

## Error Handling

### Robust Client Implementation
```python
async def safe_transfer(session, agent_id, to_address, amount_eth):
    try:
        # Always simulate first
        sim_result = await session.call_tool("simulate_transfer", {
            "agent_id": agent_id,
            "to_address": to_address,
            "amount_eth": amount_eth
        })

        sim_data = json.loads(sim_result.content[0].text)
        if sim_data.get("insufficient_funds"):
            print(f"Insufficient funds for {amount_eth} ETH transfer")
            return None

        # Execute if simulation passes
        result = await session.call_tool("execute_transfer", {
            "agent_id": agent_id,
            "to_address": to_address,
            "amount_eth": amount_eth
        })

        return result.content[0].text

    except Exception as e:
        print(f"Transfer failed: {e}")
        return None
```

## Best Practices

1. **Always simulate transfers** before execution
2. **Use testnet first** for development and testing
3. **Implement proper error handling** for network issues
4. **Monitor gas prices** before large transfers
5. **Keep private keys secure** with proper encryption
6. **Use confirmation codes** for high-value operations
7. **Export keystores regularly** for backup
8. **Monitor agent balances** to prevent insufficient funds

These examples provide a foundation for building sophisticated autonomous crypto agents using AgentVault MCP across different development environments.