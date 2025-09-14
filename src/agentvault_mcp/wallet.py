from typing import Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account
from web3.exceptions import InvalidTransaction

from . import WalletError
from .core import ContextManager, logger
from .adapters.web3_adapter import Web3Adapter


class WalletStateDict(dict):
    pass


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
        self.encryptor = Fernet(encrypt_key.encode())
        self.logger = logger.bind(component="AgentWalletManager")
        self.wallets: Dict[str, WalletStateDict] = {}  # agent_id -> WalletState-like dict

    async def spin_up_wallet(self, agent_id: str) -> str:
        """Generate and persist wallet for agent; store encrypted key."""
        await self.web3.ensure_connection()
        account = Account.create()
        encrypted_privkey = self.encryptor.encrypt(bytes(account.key))
        chain_id_value = await self.web3.w3.eth.chain_id
        wallet_state = {
            "address": account.address,
            "encrypted_privkey": encrypted_privkey,
            "chain_id": chain_id_value,
            "last_nonce": None,
        }
        self.wallets[agent_id] = wallet_state
        # Persist public parts only
        safe_state = {
            "address": account.address,
            "chain_id": chain_id_value,
        }
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
        balance_wei = await self.web3.w3.eth.get_balance(wallet["address"])
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
            privkey_bytes = self.encryptor.decrypt(wallet["encrypted_privkey"])
            account = Account.from_key(privkey_bytes)
            if account.address != wallet["address"]:
                raise WalletError("Key mismatch—security breach.")
            if amount_eth <= 0:
                raise WalletError("Amount must be positive.")
            if not self.web3.w3.is_address(to_address):
                raise WalletError("Invalid recipient address.")

            nonce = await self.web3.get_nonce(wallet["address"])
            # EIP-1559 fee fields
            priority_fee = await self.web3.w3.eth.max_priority_fee
            latest_block = await self.web3.w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas") or 0
            max_fee = base_fee + priority_fee * 2

            txn = {
                "to": to_address,
                "value": self.web3.w3.to_wei(amount_eth, "ether"),
                "nonce": nonce,
                "chainId": wallet["chain_id"],
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "type": 2,
            }
            gas_estimate = await self.web3.w3.eth.estimate_gas({**txn, "from": wallet["address"]})
            txn["gas"] = gas_estimate

            signed_txn = self.web3.w3.eth.account.sign_transaction(txn, privkey_bytes)
            tx_hash = await self.web3.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            wallet["last_nonce"] = nonce + 1

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

