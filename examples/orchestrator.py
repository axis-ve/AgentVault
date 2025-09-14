import asyncio
import os

from agentvault_mcp.core import ContextManager
from agentvault_mcp.adapters.web3_adapter import Web3Adapter
from agentvault_mcp.wallet import AgentWalletManager


async def main() -> None:
    # Zero-setup defaults (public Sepolia RPC)
    rpc_url = os.getenv("WEB3_RPC_URL") or "https://ethereum-sepolia.publicnode.com"
    encrypt_key = os.getenv("ENCRYPT_KEY") or __import__(
        "cryptography.fernet", fromlist=["Fernet"]
    ).Fernet.generate_key().decode()

    ctx = ContextManager()
    web3 = Web3Adapter(rpc_url)
    wallet = AgentWalletManager(ctx, web3, encrypt_key)

    agent_id = "demo_agent"
    address = await wallet.spin_up_wallet(agent_id)
    print(f"Wallet for {agent_id}: {address}")

    # Optional: request faucet funds if configured
    if os.getenv("AGENTVAULT_FAUCET_URL"):
        res = await wallet.request_faucet_funds(agent_id)
        print("Faucet result:", res)

    bal = await wallet.query_balance(agent_id)
    print(f"Balance: {bal} ETH")

    # Dry-run a transfer
    sim = await wallet.simulate_transfer(agent_id, "0x" + "1" * 40, 0.001)
    print("Simulation:", sim)


if __name__ == "__main__":
    asyncio.run(main())

