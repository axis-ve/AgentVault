# AgentVault CLI (agentvault)

A minimal, zero‑setup command line for wallet and strategy operations.

Install:
```bash
pip install -r requirements.txt && pip install -e .
```

Environment (optional):
- `WEB3_RPC_URL`: single RPC URL, or use `WEB3_RPC_URLS` for fallback rotation
- `WEB3_RPC_URLS`: comma‑separated RPCs used if the primary fails
- `ENCRYPT_KEY`: Fernet key; if missing, a sidecar `.key` is created
- `AGENTVAULT_STORE`: wallet store JSON path (default: agentvault_store.json)
- `AGENTVAULT_FAUCET_URL`: faucet endpoint for `faucet`

Commands:
- `create-wallet <agent_id>`: generate an ETH wallet
- `list-wallets`: show {agent_id: address}
- `balance <agent_id>`: show balance in ETH
- `simulate <agent_id> <to> <amount>`: estimate gas/fee/total
- `send <agent_id> <to> <amount> [--dry-run] [--confirmation-code CODE]`
- `faucet <agent_id> [--amount AMT]`: request faucet funds
- `export-keystore <agent_id> <passphrase>`: V3 keystore JSON
- `export-privkey <agent_id> --confirmation-code CODE`: plaintext (gated)

Strategies:
- `strategy send-when-gas-below <agent> <to> <amount> <max_gwei> [--dry-run]`
- `strategy dca-once <agent> <to> <amount> [--max-base-fee-gwei G] [--dry-run]`
- `strategy scheduled-send-once <agent> <to> <amount> <ISO8601> [--dry-run]`
- `strategy micro-tip-equal <agent> <addr1,addr2,...> <total_amount> [--dry-run]`
- `strategy micro-tip-amounts <agent> "addr=0.01,addr=0.02" [--dry-run]`

Tip Jar (QR):
- `tip-jar <agent_id> [--amount ETH] [--out path.png]`
  - Creates a wallet if needed, generates a PNG QR code with `ethereum:...` URI.

Tip Jar (HTML page):
- `tip-jar-page <agent_id> [--amount ETH] [--out path.html]`
  - Generates a minimal, brutalist‑style static HTML page with embedded QR.

Dashboard (HTML):
- `dashboard [--out path.html]`
  - Builds a static HTML dashboard listing wallets (with balances) and
    strategies with their current status. Balance fetches may take a moment on
    slow RPCs.

Examples:
```bash
agentvault create-wallet alice
agentvault faucet alice
agentvault balance alice
agentvault simulate alice 0x1111111111111111111111111111111111111111 0.001
agentvault send alice 0x1111111111111111111111111111111111111111 0.001 --dry-run
agentvault strategy send-when-gas-below alice 0x111... 0.001 12.0 --dry-run
agentvault tip-jar alice --amount 0.01 --out alice-tip.png
```

Notes:
- Use `WEB3_RPC_URLS` for better resilience; the CLI rotates on failures.
- For high value sends, configure `AGENTVAULT_MAX_TX_ETH` and `AGENTVAULT_TX_CONFIRM_CODE`.
