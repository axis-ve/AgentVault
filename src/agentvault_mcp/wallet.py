from typing import Dict

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
        chain_id_value = await self.web3.w3.eth.chain_id
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
        return account.address

    async def query_balance(self, agent_id: str) -> float:
        if agent_id not in self.wallets:
            raise WalletError(f"No wallet for {agent_id}—spin up first.")
        wallet = self.wallets[agent_id]
        await self.web3.ensure_connection()
        balance_wei = await self.web3.w3.eth.get_balance(wallet.address)
        balance_eth = self.web3.w3.from_wei(balance_wei, "ether")
        self.context.update_state(f"{agent_id}_balance", float(balance_eth))
        await self.context.append_to_history(
            "system", f"Balance for {agent_id}: {balance_eth} ETH"
        )
        self.logger.info("Balance queried", agent_id=agent_id, balance=balance_eth)
        return float(balance_eth)

    async def execute_transfer(self, agent_id: str, to_address: str, amount_eth: float) -> str:
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
            if not self.web3.w3.is_address(to_address):
                raise WalletError("Invalid recipient address.")
            # Serialize per-address nonce usage
            async with self._get_lock(wallet.address):
                nonce = await self.web3.get_nonce(wallet.address)
                # EIP-1559 fee fields
                priority_fee = await self.web3.w3.eth.max_priority_fee
                latest_block = await self.web3.w3.eth.get_block("latest")
                base_fee = latest_block.get("baseFeePerGas") or 0
                max_fee = base_fee + priority_fee * 2

                txn = {
                    "to": to_address,
                    "value": self.web3.w3.to_wei(amount_eth, "ether"),
                    "nonce": nonce,
                    "chainId": wallet.chain_id,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": priority_fee,
                    "type": 2,
                }
                gas_estimate = await self.web3.w3.eth.estimate_gas({**txn, "from": wallet.address})
                txn["gas"] = gas_estimate

                signed_txn = self.web3.w3.eth.account.sign_transaction(txn, privkey_bytes)
                tx_hash = await self.web3.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
                wallet.last_nonce = nonce + 1

            receipt = await self.web3.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
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
