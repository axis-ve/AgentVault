import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from cryptography.fernet import Fernet
from eth_account import Account
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from ollama import AsyncClient as OllamaClient  # Local LLM
from pydantic import BaseModel, Field, validator
from web3 import AsyncWeb3
from web3.exceptions import Web3Exception

# Structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
)
logger = structlog.get_logger("autonomous_mcp")

class AutonomousMCPError(Exception):
    """Base error for MCP operations."""
    pass

class WalletError(AutonomousMCPError):
    """Wallet-specific errors."""
    pass

class ContextSchema(BaseModel):
    """Internal context for agent state (autonomously managed)."""
    history: List[Dict[str, str]] = Field(default_factory=list)
    wallets: Dict[str, Dict[str, Any]] = Field(default_factory=dict)  # agent_id -> {address, encrypted_privkey, funded}
    system_prompt: str = Field(
        default="You are an autonomous crypto agent. Handle wallets, funding, and txns independently. Be helpful and secure.",
        description="Agent's core instructions."
    )

    @validator("history")
    def validate_history(cls, v):
        for msg in v:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Invalid history format.")
        return v

class FundingOption(BaseModel):
    """Funding discovery results."""
    method: str  # e.g., "faucet", "exchange"
    url: str
    description: str
    amount_suggested: float = 0.01

class AutonomousAgent:
    """Core autonomous agent: Manages tools, decisions, and LLM interactions."""
    def __init__(self):
        self.context = ContextSchema()
        self.ollama = OllamaClient()  # Local LLM - no API key
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider("https://eth-sepolia.g.alchemy.com/v2/demo"))  # Public testnet RPC
        self.encryptor = Fernet(Fernet.generate_key())  # Auto-generate encryption key (in-memory for session)
        self.logger = logger.bind(component="AutonomousAgent")

    async def ensure_connection(self) -> bool:
        """Check Web3 connection (public RPC)."""
        if await self.w3.is_connected():
            self.logger.info("Web3 connected (public RPC)")
            return True
        raise WalletError("Public RPC unavailable—retry later.")

    async def spin_up_wallet(self, wallet_id: str = "default") -> str:
        """Tool 1: Autonomous wallet creation."""
        await self.ensure_connection()
        if wallet_id in self.context.wallets:
            self.logger.info("Wallet exists", wallet_id=wallet_id)
            return self.context.wallets[wallet_id]["address"]

        account = Account.create()  # Secure random generation
        encrypted_privkey = self.encryptor.encrypt(account.key.hex().encode())
        self.context.wallets[wallet_id] = {
            "address": account.address,
            "encrypted_privkey": encrypted_privkey,
            "funded": False,
            "chain_id": await self.w3.eth.chain_id
        }
        self.context.history.append({"role": "system", "content": f"Autonomously created wallet for {wallet_id}: {account.address}"})
        self.logger.info("Wallet spun up", wallet_id=wallet_id, address=account.address)
        return account.address

    async def get_funding_options(self, wallet_id: str) -> List[FundingOption]:
        """Tool 2: Discover funding sources autonomously (faucets, exchanges)."""
        address = self.context.wallets[wallet_id]["address"]
        options = [
            FundingOption(
                method="faucet",
                url="https://sepoliafaucet.com/",
                description=f"Free testnet ETH faucet for {address} (up to 0.5 ETH/day).",
                amount_suggested=0.01
            ),
            FundingOption(
                method="exchange",
                url="https://www.coinbase.com/",
                description="Buy ETH with fiat on Coinbase and send to {address}.",
                amount_suggested=0.01
            ),
            FundingOption(
                method="exchange",
                url="https://www.binance.com/",
                description="Deposit fiat on Binance, buy ETH, withdraw to {address}.",
                amount_suggested=0.01
            )
        ]
        # Enhance with real-time API if needed (e.g., aiohttp to faucet status)
        self.context.history.append({"role": "system", "content": f"Funding options discovered for {wallet_id}: {len(options)} methods."})
        self.logger.info("Funding options generated", wallet_id=wallet_id, count=len(options))
        return [opt.dict() for opt in options]

    async def query_balance(self, wallet_id: str) -> float:
        """Tool 3: Check balance and auto-update funded status."""
        if wallet_id not in self.context.wallets:
            raise WalletError(f"No wallet for {wallet_id}—call spin_up_wallet first.")

        await self.ensure_connection()
        wallet = self.context.wallets[wallet_id]
        balance_wei = await self.w3.eth.get_balance(wallet["address"])
        balance_eth = self.w3.from_wei(balance_wei, "ether")

        if balance_eth >= 0.01:  # Threshold for "funded"
            wallet["funded"] = True

        self.context.history.append({"role": "system", "content": f"Balance for {wallet_id}: {balance_eth} ETH (funded: {wallet['funded']})"})
        self.logger.info("Balance queried", wallet_id=wallet_id, balance=balance_eth)
        return float(balance_eth)

    async def execute_transfer(self, wallet_id: str, to_address: str, amount_eth: float) -> str:
        """Tool 4: Autonomous txn execution (sign/send/confirm)."""
        if wallet_id not in self.context.wallets or not self.context.wallets[wallet_id]["funded"]:
            raise WalletError(f"Wallet {wallet_id} not funded—fund first.")

        wallet = self.context.wallets[wallet_id]
        try:
            privkey_bytes = self.encryptor.decrypt(wallet["encrypted_privkey"])
            privkey_hex = privkey_bytes.decode()
            account = Account.from_key(privkey_hex)

            # Validate
            if not self.w3.is_address(to_address):
                raise ValueError("Invalid recipient address.")
            if amount_eth <= 0 or amount_eth > await self.query_balance(wallet_id):
                raise ValueError("Invalid amount.")

            nonce = await self.w3.eth.get_transaction_count(account.address)
            txn = {
                "to": to_address,
                "value": self.w3.to_wei(amount_eth, "ether"),
                "gas": 21000,
                "gasPrice": await self.w3.eth.gas_price,
                "nonce": nonce,
                "chainId": wallet["chain_id"],
            }
            signed_txn = self.w3.eth.account.sign_transaction(txn, privkey_hex)
            tx_hash = await self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            receipt = await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                raise WalletError("Transaction failed on-chain.")

            self.context.history.append({"role": "system", "content": f"Transfer executed: {amount_eth} ETH to {to_address}. Hash: {tx_hash.hex()}"})
            self.logger.info("Transfer executed", wallet_id=wallet_id, tx_hash=tx_hash.hex(), amount=amount_eth)
            return tx_hash.hex()

        except Exception as e:
            self.logger.error("Transfer failed", wallet_id=wallet_id, error=str(e))
            raise WalletError(f"Transfer error: {e}")

    async def autonomous_action(self, user_query: str, wallet_id: str = "default") -> str:
        """Tool 5: Agent's decision engine—analyzes context and acts."""
        # Step 1: Ensure wallet ready
        await self.spin_up_wallet(wallet_id)
        balance = await self.query_balance(wallet_id)
        if not self.context.wallets[wallet_id]["funded"]:
            options = await self.get_funding_options(wallet_id)
            funding_msg = "Wallet needs funding. Options: " + "; ".join([f"{opt['method']}: {opt['url']}" for opt in options])
            self.context.history.append({"role": "assistant", "content": funding_msg})
            self.logger.info("Autonomous funding prompt", wallet_id=wallet_id)
            return funding_msg

        # Step 2: LLM-driven decision (local, no key)
        full_context = [{"role": "system", "content": self.context.system_prompt}] + self.context.history + [
            {"role": "user", "content": user_query}
        ]
        try:
            response = await self.ollama.chat(
                model="llama3.1",
                messages=full_context,
                stream=False,
                options={"temperature": 0.7, "num_predict": 200}
            )
            agent_reply = response["message"]["content"]
            self.context.history.append({"role": "assistant", "content": agent_reply})

            # Step 3: Act if needed (rule-based + LLM intent)
            if "send" in user_query.lower() or "transfer" in agent_reply.lower():
                # Parse simple intent (extend with NLP for prod)
                to_addr = "0x..."  # Extract from query/LLM (use regex or LLM structured output)
                amount = 0.01  # Similarly extract
                tx_hash = await self.execute_transfer(wallet_id, to_addr, amount)
                agent_reply += f"\nExecuted: {tx_hash}"
            elif "low" in user_query.lower() or balance < 0.005:
                agent_reply += f"\nLow balance ({balance} ETH). Suggesting conservative hold or small faucet top-up."

            self.logger.info("Autonomous action completed", wallet_id=wallet_id, query=user_query, reply_len=len(agent_reply))
            return agent_reply

        except Exception as e:
            self.logger.error("LLM decision failed", error=str(e))
            raise AutonomousMCPError(f"Agent decision error: {e}")

# FastAPI Server for User Interaction (Optional: Run agent in background)
app = FastAPI(title="Autonomous MCP Server", version="1.0.0")
agent = AutonomousAgent()  # Global instance (thread-safe for prod)

class ChatRequest(BaseModel):
    message: str
    wallet_id: str = "default"

@app.post("/chat", response_model=dict)
async def chat(request: ChatRequest):
    try:
        reply = await agent.autonomous_action(request.message, request.wallet_id)
        return {"reply": reply, "context_summary": agent.context.history[-3:]}  # Last 3 for brevity
    except AutonomousMCPError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "Autonomous MCP ready - No setup needed!"}

# Background agent loop (proactive monitoring, e.g., every 5min)
async def background_monitor():
    while True:
        for wallet_id in agent.context.wallets:
            balance = await agent.query_balance(wallet_id)
            if balance < 0.001:
                await agent.get_funding_options(wallet_id)  # Log/alert
        await asyncio.sleep(300)  # 5min

if __name__ == "__main__":
    import uvicorn
    # Start background monitor
    asyncio.create_task(background_monitor())
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)