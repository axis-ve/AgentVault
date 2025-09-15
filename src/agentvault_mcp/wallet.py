from typing import Dict
import os
import json
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account
from pydantic import BaseModel
from web3.exceptions import InvalidTransaction

from . import WalletError
from .core import ContextManager, logger
from .adapters.web3_adapter import Web3Adapter


class WalletState(BaseModel):
    address: str
    encrypted_privkey: bytes
    chain_id: int
    last_nonce: int | None = None


class AgentWalletManager:
    """Wallet-specific MCP layer: Secure, async wallet ops with context integration."""

    def __init__(
        self,
        context_manager: ContextManager,
        web3_adapter: Web3Adapter,
        encrypt_key: str,
        persist_path: str | None = None,
        logger=logger,
    ):
        self.context = context_manager
        self.web3 = web3_adapter
        # Validate Fernet key early
        try:
            self.encryptor = Fernet(encrypt_key.encode())
        except Exception as e:
            raise WalletError("Invalid ENCRYPT_KEY: must be a base64-encoded 32-byte Fernet key") from e
        self.logger = logger.bind(component="AgentWalletManager")
        self.wallets: Dict[str, WalletState] = {}  # agent_id -> WalletState
        # Per-address nonce lock to avoid concurrent nonce races
        import asyncio
        self._locks: Dict[str, asyncio.Lock] = {}
        # Optional persistence
        self.persist_path = Path(persist_path or os.getenv("AGENTVAULT_STORE", "agentvault_store.json")).resolve()
        self._load_persisted()

    def _get_lock(self, address: str):
        import asyncio
        if address not in self._locks:
            self._locks[address] = asyncio.Lock()
        return self._locks[address]

    async def spin_up_wallet(self, agent_id: str) -> str:
        """Generate and persist wallet for agent; store encrypted key."""
        await self.web3.ensure_connection()
        # Ensure uniqueness across current process by regenerating on extremely unlikely collision
        existing_addresses = {w.address for w in self.wallets.values()}
        account = Account.create()
        while account.address in existing_addresses:
            account = Account.create()
        encrypted_privkey = self.encryptor.encrypt(bytes(account.key))
        # Accept both sync and awaitable chain_id
        import asyncio as _asyncio
        cid = self.web3.w3.eth.chain_id
        chain_id_value = await cid if _asyncio.iscoroutine(cid) else cid
        wallet_state = WalletState(
            address=account.address,
            encrypted_privkey=encrypted_privkey,
            chain_id=chain_id_value,
        )
        self.wallets[agent_id] = wallet_state
        # Persist public parts only
        safe_state = wallet_state.model_dump(exclude={"encrypted_privkey", "last_nonce"})
        self.context.update_state(f"{agent_id}_wallet", safe_state)
        await self.context.append_to_history(
            "system", f"Wallet created for {agent_id}: {account.address}"
        )
        self.logger.info("Wallet spun up", agent_id=agent_id, address=account.address)
        self._persist()
        return account.address

    async def query_balance(self, agent_id: str) -> float:
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}—spin up first.")
        wallet = self.wallets[agent_id]
        await self.web3.ensure_connection()
        balance_wei = await self.web3.get_balance(wallet.address)
        balance_eth = self.web3.from_wei(balance_wei, "ether")
        self.context.update_state(f"{agent_id}_balance", float(balance_eth))
        await self.context.append_to_history(
            "system", f"Balance for {agent_id}: {balance_eth} ETH"
        )
        self.logger.info("Balance queried", agent_id=agent_id, balance=balance_eth)
        return float(balance_eth)

    async def execute_transfer(self, agent_id: str, to_address: str, amount_eth: float, confirmation_code: str | None = None) -> str:
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")
        wallet = self.wallets[agent_id]
        try:
            privkey_bytes = self.encryptor.decrypt(wallet.encrypted_privkey)
            account = Account.from_key(privkey_bytes)
            if account.address != wallet.address:
                raise WalletError("Key mismatch—security breach.")
            if amount_eth <= 0:
                raise WalletError("Amount must be positive.")
            if not self.web3.is_address(to_address):
                raise WalletError("Invalid recipient address.")
            # Spending limit guard
            self._enforce_spend_limit(amount_eth, confirmation_code)
            # Serialize per-address nonce usage
            async with self._get_lock(wallet.address):
                nonce = await self.web3.get_nonce(wallet.address)
                # EIP-1559 fee fields
                priority_fee = await self.web3.max_priority_fee()
                latest_block = await self.web3.get_block_latest()
                base_fee = latest_block.get("baseFeePerGas") or 0
                # Conservative headroom for base fee spikes
                max_fee = base_fee * 2 + priority_fee

                txn = {
                    "to": to_address,
                    "value": self.web3.to_wei(amount_eth, "ether"),
                    "nonce": nonce,
                    "chainId": wallet.chain_id,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": priority_fee,
                    "type": 2,
                }
                gas_estimate = await self.web3.estimate_gas({**txn, "from": wallet.address})
                # Pre-check funds: amount + max fee must be available
                bal_wei = await self.web3.get_balance(wallet.address)
                total_cost_wei = txn["value"] + gas_estimate * max_fee
                if bal_wei < total_cost_wei:
                    raise WalletError("Insufficient funds for amount + fees.")
                txn["gas"] = gas_estimate

                signed_txn = self.web3.w3.eth.account.sign_transaction(txn, privkey_bytes)
                tx_hash = await self.web3.send_raw_transaction(signed_txn.rawTransaction)
                wallet.last_nonce = nonce + 1

            receipt = await self.web3.wait_for_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                raise WalletError("Transaction failed on-chain.")

            await self.context.append_to_history(
                "system",
                f"Transfer executed for {agent_id}: {amount_eth} ETH to {to_address}. Hash: {tx_hash.hex()}",
            )
            self.logger.info(
                "Transfer successful", agent_id=agent_id, tx_hash=tx_hash.hex(), amount=amount_eth
            )
            return tx_hash.hex()
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except InvalidTransaction as e:
            self.logger.error("Invalid txn", error=str(e), agent_id=agent_id)
            raise WalletError(f"Transaction invalid: {e}")
        except Exception as e:
            self.logger.error("Transfer failed", error=str(e), agent_id=agent_id)
            raise WalletError(f"Transfer error: {e}")

    async def list_wallets(self) -> dict[str, str]:
        """Return a mapping of agent_id -> wallet address (no secrets)."""
        return {aid: ws.address for aid, ws in self.wallets.items()}

    async def export_wallet_keystore(self, agent_id: str, passphrase: str) -> str:
        """Export the specified agent's wallet as an encrypted V3 keystore JSON string.

        This is safe to share or back up if the passphrase is strong. Never return
        plaintext private keys by default.
        """
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")
        try:
            privkey_bytes = self.encryptor.decrypt(self.wallets[agent_id].encrypted_privkey)
            # eth-account can encrypt raw private key bytes into V3 keystore
            keystore_dict = Account.encrypt(privkey_bytes, passphrase)
            import json as _json
            return _json.dumps(keystore_dict)
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except Exception as e:
            raise WalletError(f"Keystore export failed: {e}")

    async def export_wallet_private_key(self, agent_id: str, confirmation_code: str | None = None) -> str:
        """Export plaintext private key (hex). Strongly discouraged.

        Requires AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1 and a matching AGENTVAULT_EXPORT_CODE
        provided via the 'confirmation_code' parameter. Use export_wallet_keystore instead when possible.
        """
        import os
        if os.getenv("AGENTVAULT_ALLOW_PLAINTEXT_EXPORT") != "1":
            raise WalletError("Plaintext export disabled. Set AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1 to enable.")
        server_code = os.getenv("AGENTVAULT_EXPORT_CODE")
        if not server_code or not confirmation_code or confirmation_code != server_code:
            raise WalletError("Plaintext export requires a valid confirmation code.")
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")
        try:
            privkey_bytes = self.encryptor.decrypt(self.wallets[agent_id].encrypted_privkey)
            return "0x" + privkey_bytes.hex()
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except Exception as e:
            raise WalletError(f"Private key export failed: {e}")

    async def simulate_transfer(self, agent_id: str, to_address: str, amount_eth: float) -> dict:
        """Simulate a transfer without broadcasting. Returns a summary dict.

        Includes estimated gas, fees, and total cost in ETH.
        """
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")
        wallet = self.wallets[agent_id]
        if amount_eth <= 0:
            raise WalletError("Amount must be positive.")
        if not self.web3.is_address(to_address):
            raise WalletError("Invalid recipient address.")
        # Fee estimation
        priority_fee = await self.web3.max_priority_fee()
        latest_block = await self.web3.get_block_latest()
        base_fee = latest_block.get("baseFeePerGas") or 0
        max_fee = base_fee * 2 + priority_fee
        txn = {
            "to": to_address,
            "value": self.web3.to_wei(amount_eth, "ether"),
            "chainId": wallet.chain_id,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "type": 2,
        }
        gas_estimate = await self.web3.estimate_gas({**txn, "from": wallet.address})
        total_fee_wei = gas_estimate * max_fee
        total_fee_eth = float(self.web3.from_wei(total_fee_wei, "ether"))
        total_eth = amount_eth + total_fee_eth
        return {
            "from": wallet.address,
            "to": to_address,
            "amount_eth": amount_eth,
            "gas": int(gas_estimate),
            "max_fee_per_gas": int(max_fee),
            "max_priority_fee_per_gas": int(priority_fee),
            "estimated_fee_eth": total_fee_eth,
            "estimated_total_eth": total_eth,
            "insufficient_funds": float(
                self.web3.from_wei(await self.web3.get_balance(wallet.address), "ether")
            )
            < amount_eth + total_fee_eth,
        }

    async def request_faucet_funds(self, agent_id: str, amount_eth: float | None = None, timeout_s: int = 60) -> dict:
        """Request testnet funds from a faucet and wait for balance change.

        Requires env AGENTVAULT_FAUCET_URL. Returns a status dict.
        """
        faucet_url = os.getenv("AGENTVAULT_FAUCET_URL")
        if not faucet_url:
            raise WalletError("AGENTVAULT_FAUCET_URL not configured")
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}.")
        addr = self.wallets[agent_id].address
        import httpx
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {"address": addr}
                if amount_eth is not None:
                    payload["amount_eth"] = amount_eth
                resp = await client.post(faucet_url, json=payload)
                ok = resp.status_code in (200, 201, 202)
                start_bal = float(self.web3.from_wei(await self.web3.get_balance(addr), "ether"))
                if not ok:
                    return {"ok": False, "status": resp.status_code, "balance": start_bal}
                # Poll for balance increase
                import asyncio
                end_bal = start_bal
                deadline = asyncio.get_event_loop().time() + timeout_s
                while asyncio.get_event_loop().time() < deadline:
                    await asyncio.sleep(5)
                    end_bal = float(self.web3.from_wei(await self.web3.get_balance(addr), "ether"))
                    if end_bal > start_bal:
                        break
                return {"ok": end_bal > start_bal, "start_balance": start_bal, "end_balance": end_bal}
        except Exception as e:
            raise WalletError(f"Faucet request failed: {e}")

    # ---------- Internal helpers ----------
    def _enforce_spend_limit(self, amount_eth: float, confirmation_code: str | None = None) -> None:
        """Require confirmation above configured threshold.

        Env:
          - AGENTVAULT_MAX_TX_ETH: float threshold; if unset, no gating
          - AGENTVAULT_TX_CONFIRM_CODE: server-side secret; must match provided code
        """
        max_tx_env = os.getenv("AGENTVAULT_MAX_TX_ETH")
        if not max_tx_env:
            return
        try:
            threshold = float(max_tx_env)
        except ValueError:
            return
        if amount_eth <= threshold:
            return
        server_code = os.getenv("AGENTVAULT_TX_CONFIRM_CODE")
        if not server_code or confirmation_code != server_code:
            raise WalletError(
                f"Transfer exceeds limit ({amount_eth} ETH > {threshold} ETH). Confirmation code required."
            )

    def _load_persisted(self) -> None:
        try:
            if not self.persist_path.exists():
                return
            with open(self.persist_path, "r") as f:
                data = json.load(f)
            loaded = 0
            for agent_id, rec in data.items():
                try:
                    ws = WalletState(
                        address=rec["address"],
                        encrypted_privkey=bytes.fromhex(rec["encrypted_privkey_hex"]),
                        chain_id=int(rec["chain_id"]),
                        last_nonce=rec.get("last_nonce"),
                    )
                    self.wallets[agent_id] = ws
                    loaded += 1
                except Exception:
                    continue
            if loaded:
                self.logger.info("Persisted wallets loaded", count=loaded, path=str(self.persist_path))
        except Exception as e:
            self.logger.warning("Failed to load persisted wallets", error=str(e))

    def _persist(self) -> None:
        try:
            serial = {
                agent_id: {
                    "address": ws.address,
                    "chain_id": ws.chain_id,
                    "last_nonce": ws.last_nonce,
                    "encrypted_privkey_hex": ws.encrypted_privkey.hex(),
                }
                for agent_id, ws in self.wallets.items()
            }
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", delete=False, dir=str(self.persist_path.parent)) as tf:
                json.dump(serial, tf, indent=2)
                tmp_name = tf.name
            os.replace(tmp_name, self.persist_path)
        except Exception as e:
            self.logger.warning("Failed to persist wallets", error=str(e))
