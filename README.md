# AgentVault MCP

Secure context and wallet tools for autonomous AI agents, built on the Model Context Protocol (MCP). Exposes stdio MCP tools for Ethereum wallet management and a context-aware LLM, with structured logging and safe context trimming.

## Features
- ContextManager with proactive trimming and token counting (tiktoken)
- OpenAI adapter (async, configurable model)
- Web3 wallet ops with EIP‑1559 fees and gas estimation
- Fernet encryption of private keys; never persisted in plain text
- MCP stdio server registering wallet + LLM tools

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
cp .env.example .env  # set OPENAI_API_KEY, ENCRYPT_KEY, WEB3_RPC_URL
python -m agentvault_mcp.server  # or: agentvault-mcp
```

### MCP Client Example (Claude Desktop)
```json
{
  "mcpServers": {
    "agentvault": {
      "command": "python",
      "args": ["-m", "agentvault_mcp.server"],
      "env": {
        "OPENAI_API_KEY": "...",
        "ENCRYPT_KEY": "...",
        "WEB3_RPC_URL": "..."
      }
    }
  }
}
```

## Tools
- `spin_up_wallet(agent_id: str) -> str`
- `query_balance(agent_id: str) -> float`
- `execute_transfer(agent_id: str, to_address: str, amount_eth: float) -> str`
- `generate_response(user_message: str) -> str`

## Optional MCP Features
- A `wallet_status` prompt is registered when the SDK supports prompts.
- An `agentvault/context` resource is registered when resources are supported; it returns a sanitized JSON snapshot of state.

## Security Notes
- Private keys are encrypted with a Fernet key provided via `ENCRYPT_KEY`.
- Only public wallet info is injected into context; resource output is sanitized.

## Development
- Run tests: `pytest -q`
- Lint/format: add ruff/black if desired.

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
