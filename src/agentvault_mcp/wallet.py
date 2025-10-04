from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken
from eth_account import Account
from eth_account.hdaccount import generate_mnemonic
from eth_account.messages import encode_defunct, encode_typed_data
from pydantic import BaseModel
from web3 import Web3
from web3.exceptions import InvalidTransaction

from . import WalletError
from .core import ContextManager, logger
from .adapters.web3_adapter import Web3Adapter
from .db.cli import upgrade
from .db.engine import get_session_maker
from .db.repositories import WalletRepository

_ERC20_METADATA_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
]


class WalletState(BaseModel):
    wallet_id: str
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
        *,
        database_url: str | None = None,
        tenant_id: str = "default",
        auto_migrate: bool = True,
        logger=logger,
    ):
        self.context = context_manager
        self.web3 = web3_adapter
        try:
            self.encryptor = Fernet(encrypt_key.encode())
        except Exception as e:  # pragma: no cover - defensive check
            raise WalletError(
                "Invalid ENCRYPT_KEY: must be a base64-encoded 32-byte Fernet key"
            ) from e
        self.logger = logger.bind(component="AgentWalletManager")
        self._locks: Dict[str, asyncio.Lock] = {}
        self.wallets: Dict[str, WalletState] = {}
        self.database_url = database_url
        self.tenant_id = tenant_id
        self.session_maker = get_session_maker(database_url)
        if auto_migrate:
            try:
                upgrade(database_url)
            except Exception as exc:  # pragma: no cover - start-up failure should surface
                self.logger.error("Database migration failed", error=str(exc))
                raise

    def _get_lock(self, address: str) -> asyncio.Lock:
        if address not in self._locks:
            self._locks[address] = asyncio.Lock()
        return self._locks[address]

    async def _wallet_exists(self, agent_id: str) -> bool:
        if agent_id in self.wallets:
            return True
        async with self.session_maker() as session:
            repo = WalletRepository(session, self.tenant_id)
            record = await repo.get_by_agent_id(agent_id)
            return record is not None

    def _cache_wallet_state(self, agent_id: str, state: WalletState) -> WalletState:
        self.wallets[agent_id] = state
        safe_state = state.model_dump(exclude={"encrypted_privkey", "last_nonce", "wallet_id"})
        self.context.update_state(f"{agent_id}_wallet", safe_state)
        return state

    async def _hydrate_wallet_from_db(self, agent_id: str) -> WalletState:
        async with self.session_maker() as session:
            repo = WalletRepository(session, self.tenant_id)
            record = await repo.get_by_agent_id(agent_id)
            if not record:
                raise WalletError(f"No wallet for {agent_id}.")
            state = WalletState(
                wallet_id=record.id,
                address=record.address,
                encrypted_privkey=record.encrypted_privkey,
                chain_id=record.chain_id,
                last_nonce=record.last_nonce,
            )
            return self._cache_wallet_state(agent_id, state)

    async def _get_wallet_state(self, agent_id: str) -> WalletState:
        if agent_id in self.wallets:
            return self.wallets[agent_id]
        return await self._hydrate_wallet_from_db(agent_id)

    async def _load_account(self, agent_id: str) -> Account:
        state = await self._get_wallet_state(agent_id)
        try:
            privkey_bytes = self.encryptor.decrypt(state.encrypted_privkey)
        except InvalidToken as exc:
            raise WalletError("Decryption failed—check encrypt key.") from exc
        return Account.from_key(privkey_bytes)

    async def _store_wallet(
        self,
        agent_id: str,
        account: Account,
        chain_id: int,
        *,
        event: str,
    ) -> str:
        encrypted_privkey = self.encryptor.encrypt(bytes(account.key))
        async with self.session_maker() as session:
            async with session.begin():
                repo = WalletRepository(session, self.tenant_id)
                record = await repo.upsert_wallet(
                    agent_id=agent_id,
                    address=account.address,
                    encrypted_privkey=encrypted_privkey,
                    chain_id=chain_id,
                    last_nonce=None,
                    metadata_json={},
                )
        state = WalletState(
            wallet_id=record.id,
            address=account.address,
            encrypted_privkey=encrypted_privkey,
            chain_id=chain_id,
        )
        self._cache_wallet_state(agent_id, state)
        await self.context.append_to_history(
            "system", f"Wallet {event} for {agent_id}: {account.address}"
        )
        self.logger.info("Wallet %s", event, agent_id=agent_id, address=account.address)
        return account.address

    async def spin_up_wallet(self, agent_id: str) -> str:
        await self.web3.ensure_connection()
        existing_addresses = {w.address for w in self.wallets.values()}
        account = Account.create()
        while account.address in existing_addresses:
            account = Account.create()
        chain_id = self.web3.w3.eth.chain_id
        chain_id_value = await chain_id if asyncio.iscoroutine(chain_id) else chain_id
        return await self._store_wallet(agent_id, account, chain_id_value, event="created")

    async def import_wallet_from_private_key(
        self, agent_id: str, private_key: str, *, rotate: bool = False
    ) -> str:
        if not rotate and await self._wallet_exists(agent_id):
            raise WalletError(
                f"Wallet for {agent_id} already exists—pass rotate=True to overwrite."
            )
        await self.web3.ensure_connection()
        account = Account.from_key(private_key)
        chain_id = self.web3.w3.eth.chain_id
        chain_id_value = await chain_id if asyncio.iscoroutine(chain_id) else chain_id
        return await self._store_wallet(
            agent_id, account, chain_id_value, event="imported_from_private_key"
        )

    async def import_wallet_from_mnemonic(
        self,
        agent_id: str,
        mnemonic: str,
        *,
        path: str | None = None,
        passphrase: str | None = None,
        rotate: bool = False,
    ) -> str:
        if not rotate and await self._wallet_exists(agent_id):
            raise WalletError(
                f"Wallet for {agent_id} already exists—pass rotate=True to overwrite."
            )
        await self.web3.ensure_connection()
        account = Account.from_mnemonic(mnemonic, account_path=path, passphrase=passphrase or "")
        chain_id = self.web3.w3.eth.chain_id
        chain_id_value = await chain_id if asyncio.iscoroutine(chain_id) else chain_id
        return await self._store_wallet(
            agent_id, account, chain_id_value, event="imported_from_mnemonic"
        )

    async def import_wallet_from_encrypted_json(
        self, agent_id: str, encrypted_json: str, password: str, *, rotate: bool = False
    ) -> str:
        if not rotate and await self._wallet_exists(agent_id):
            raise WalletError(
                f"Wallet for {agent_id} already exists—pass rotate=True to overwrite."
            )
        try:
            account = Account.from_key(Account.decrypt(encrypted_json, password))
        except Exception as exc:  # pragma: no cover - depends on eth-account internals
            raise WalletError(f"Failed to decrypt keystore: {exc}") from exc
        await self.web3.ensure_connection()
        chain_id = self.web3.w3.eth.chain_id
        chain_id_value = await chain_id if asyncio.iscoroutine(chain_id) else chain_id
        return await self._store_wallet(
            agent_id, account, chain_id_value, event="imported_from_keystore"
        )

    async def generate_mnemonic(self, *, num_words: int = 12, language: str = "english") -> str:
        return generate_mnemonic(num_words=num_words, lang=language)

    async def encrypt_wallet_json(self, agent_id: str, password: str) -> str:
        state = await self._get_wallet_state(agent_id)
        try:
            privkey = self.encryptor.decrypt(state.encrypted_privkey)
            keystore = Account.encrypt(privkey, password)
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except Exception as exc:  # pragma: no cover - depends on eth-account internals
            raise WalletError(f"Failed to encrypt wallet: {exc}") from exc
        import json as _json

        return _json.dumps(keystore)

    async def decrypt_wallet_json(self, encrypted_json: str, password: str) -> Dict[str, Any]:
        try:
            priv_bytes = Account.decrypt(encrypted_json, password)
            account = Account.from_key(priv_bytes)
        except Exception as exc:
            raise WalletError(f"Failed to decrypt keystore: {exc}") from exc
        return {"address": account.address, "private_key": "0x" + priv_bytes.hex()}

    async def sign_message(self, agent_id: str, message: str) -> Dict[str, Any]:
        account = await self._load_account(agent_id)
        signable = encode_defunct(text=message)
        signature = account.sign_message(signable)
        return {
            "signature": signature.signature.hex(),
            "message_hash": signature.message_hash.hex(),
        }

    async def verify_message(self, address: str, message: str, signature: str) -> Dict[str, Any]:
        signable = encode_defunct(text=message)
        recovered = Account.recover_message(signable, signature=signature)
        return {
            "valid": recovered.lower() == address.lower(),
            "recovered_address": recovered,
        }

    async def sign_typed_data(self, agent_id: str, typed_data: Dict[str, Any]) -> Dict[str, Any]:
        account = await self._load_account(agent_id)
        if isinstance(typed_data, str):
            import json as _json

            typed_data = _json.loads(typed_data)
        signable = encode_typed_data(full_message=typed_data)
        signature = account.sign_message(signable)
        return {
            "signature": signature.signature.hex(),
            "message_hash": signature.message_hash.hex(),
        }

    async def verify_typed_data(
        self, address: str, typed_data: Dict[str, Any], signature: str
    ) -> Dict[str, Any]:
        if isinstance(typed_data, str):
            import json as _json

            typed_data = _json.loads(typed_data)
        signable = encode_typed_data(full_message=typed_data)
        recovered = Account.recover_message(signable, signature=signature)
        return {
            "valid": recovered.lower() == address.lower(),
            "recovered_address": recovered,
        }

    async def query_balance(self, agent_id: str) -> float:
        state = await self._get_wallet_state(agent_id)
        await self.web3.ensure_connection()
        balance_wei = await self.web3.get_balance(state.address)
        balance_eth = self.web3.from_wei(balance_wei, "ether")
        self.context.update_state(f"{agent_id}_balance", float(balance_eth))
        await self.context.append_to_history(
            "system", f"Balance for {agent_id}: {balance_eth} ETH"
        )
        self.logger.info("Balance queried", agent_id=agent_id, balance=balance_eth)
        return float(balance_eth)

    async def execute_transfer(
        self,
        agent_id: str,
        to_address: str,
        amount_eth: float,
        confirmation_code: str | None = None,
    ) -> str:
        state = await self._get_wallet_state(agent_id)
        try:
            privkey_bytes = self.encryptor.decrypt(state.encrypted_privkey)
            account = Account.from_key(privkey_bytes)
            if account.address != state.address:
                raise WalletError("Key mismatch—security breach.")
            if amount_eth <= 0:
                raise WalletError("Amount must be positive.")
            if not self.web3.is_address(to_address):
                raise WalletError("Invalid recipient address.")
            self._enforce_spend_limit(amount_eth, confirmation_code)
            async with self._get_lock(state.address):
                nonce = await self.web3.get_nonce(state.address)
                priority_fee = await self.web3.max_priority_fee()
                latest_block = await self.web3.get_block_latest()
                base_fee = latest_block.get("baseFeePerGas") or 0
                max_fee = base_fee * 2 + priority_fee

                txn = {
                    "to": to_address,
                    "value": self.web3.to_wei(amount_eth, "ether"),
                    "nonce": nonce,
                    "chainId": state.chain_id,
                    "maxFeePerGas": max_fee,
                    "maxPriorityFeePerGas": priority_fee,
                    "type": 2,
                }
                gas_estimate = await self.web3.estimate_gas({**txn, "from": state.address})
                bal_wei = await self.web3.get_balance(state.address)
                total_cost_wei = txn["value"] + gas_estimate * max_fee
                if bal_wei < total_cost_wei:
                    raise WalletError("Insufficient funds for amount + fees.")
                txn["gas"] = gas_estimate

                signed_txn = self.web3.w3.eth.account.sign_transaction(txn, privkey_bytes)
                tx_hash = await self.web3.send_raw_transaction(signed_txn.rawTransaction)
                state.last_nonce = nonce + 1

            receipt = await self.web3.wait_for_receipt(tx_hash, timeout=120)
            if receipt.status != 1:
                raise WalletError("Transaction failed on-chain.")

            async with self.session_maker() as session:
                async with session.begin():
                    repo = WalletRepository(session, self.tenant_id)
                    await repo.update_last_nonce(agent_id, state.last_nonce)

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
        except WalletError:
            raise
        except Exception as e:
            self.logger.error("Transfer failed", error=str(e), agent_id=agent_id)
            raise WalletError(f"Transfer error: {e}")

    async def list_wallets(self) -> dict[str, str]:
        async with self.session_maker() as session:
            repo = WalletRepository(session, self.tenant_id)
            records = await repo.list_wallets()
        result: dict[str, str] = {}
        for record in records:
            state = WalletState(
                wallet_id=record.id,
                address=record.address,
                encrypted_privkey=record.encrypted_privkey,
                chain_id=record.chain_id,
                last_nonce=record.last_nonce,
            )
            self._cache_wallet_state(record.agent_id, state)
            result[record.agent_id] = record.address
        return result

    async def export_wallet_keystore(self, agent_id: str, passphrase: str) -> str:
        state = await self._get_wallet_state(agent_id)
        try:
            privkey_bytes = self.encryptor.decrypt(state.encrypted_privkey)
            keystore_dict = Account.encrypt(privkey_bytes, passphrase)
            import json as _json

            return _json.dumps(keystore_dict)
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except Exception as e:
            raise WalletError(f"Keystore export failed: {e}")

    async def export_wallet_private_key(
        self, agent_id: str, confirmation_code: str | None = None
    ) -> str:
        if os.getenv("AGENTVAULT_ALLOW_PLAINTEXT_EXPORT") != "1":
            raise WalletError(
                "Plaintext export disabled. Set AGENTVAULT_ALLOW_PLAINTEXT_EXPORT=1 to enable."
            )
        server_code = os.getenv("AGENTVAULT_EXPORT_CODE")
        if not server_code or not confirmation_code or confirmation_code != server_code:
            raise WalletError("Plaintext export requires a valid confirmation code.")
        state = await self._get_wallet_state(agent_id)
        try:
            privkey_bytes = self.encryptor.decrypt(state.encrypted_privkey)
            return "0x" + privkey_bytes.hex()
        except InvalidToken:
            raise WalletError("Decryption failed—check encrypt key.")
        except Exception as e:  # pragma: no cover
            raise WalletError(f"Private key export failed: {e}")

    async def simulate_transfer(self, agent_id: str, to_address: str, amount_eth: float) -> dict:
        state = await self._get_wallet_state(agent_id)
        if amount_eth <= 0:
            raise WalletError("Amount must be positive.")
        if not self.web3.is_address(to_address):
            raise WalletError("Invalid recipient address.")
        priority_fee = await self.web3.max_priority_fee()
        latest_block = await self.web3.get_block_latest()
        base_fee = latest_block.get("baseFeePerGas") or 0
        max_fee = base_fee * 2 + priority_fee
        txn = {
            "to": to_address,
            "value": self.web3.to_wei(amount_eth, "ether"),
            "chainId": state.chain_id,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority_fee,
            "type": 2,
        }
        gas_estimate = await self.web3.estimate_gas({**txn, "from": state.address})
        total_fee_wei = gas_estimate * max_fee
        total_fee_eth = float(self.web3.from_wei(total_fee_wei, "ether"))
        total_eth = amount_eth + total_fee_eth
        balance_eth = float(
            self.web3.from_wei(await self.web3.get_balance(state.address), "ether")
        )
        return {
            "from": state.address,
            "to": to_address,
            "amount_eth": amount_eth,
            "gas": int(gas_estimate),
            "max_fee_per_gas": int(max_fee),
            "max_priority_fee_per_gas": int(priority_fee),
            "estimated_fee_eth": total_fee_eth,
            "estimated_total_eth": total_eth,
            "insufficient_funds": balance_eth < total_eth,
        }

    async def request_faucet_funds(
        self, agent_id: str, amount_eth: float | None = None, timeout_s: int = 60
    ) -> dict:
        faucet_url = os.getenv("AGENTVAULT_FAUCET_URL")
        if not faucet_url:
            raise WalletError("AGENTVAULT_FAUCET_URL not configured")
        state = await self._get_wallet_state(agent_id)
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                payload = {"address": state.address}
                if amount_eth is not None:
                    payload["amount_eth"] = amount_eth
                resp = await client.post(faucet_url, json=payload)
                ok = resp.status_code in (200, 201, 202)
                start_bal = float(self.web3.from_wei(await self.web3.get_balance(state.address), "ether"))
                if not ok:
                    return {"ok": False, "status": resp.status_code, "balance": start_bal}
                end_bal = start_bal
                deadline = asyncio.get_event_loop().time() + timeout_s
                while asyncio.get_event_loop().time() < deadline:
                    await asyncio.sleep(5)
                    end_bal = float(
                        self.web3.from_wei(await self.web3.get_balance(state.address), "ether")
                    )
                    if end_bal > start_bal:
                        break
                return {"ok": end_bal > start_bal, "start_balance": start_bal, "end_balance": end_bal}
        except Exception as e:
            raise WalletError(f"Faucet request failed: {e}")

    def _enforce_spend_limit(self, amount_eth: float, confirmation_code: str | None = None) -> None:
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

    async def provider_status(self) -> Dict[str, Any]:
        await self.web3.ensure_connection()
        chain_id_val = self.web3.w3.eth.chain_id
        chain_id = await chain_id_val if asyncio.iscoroutine(chain_id_val) else chain_id_val
        latest_block = await self.web3.get_block_latest()
        block_number = latest_block.get("number")
        block_time = latest_block.get("timestamp")
        base_fee = latest_block.get("baseFeePerGas")
        priority_fee = None
        try:
            priority_fee = await self.web3.max_priority_fee()
        except Exception:
            priority_fee = None
        gas_price_gwei = None
        if base_fee is not None:
            base_fee_gwei = float(self.web3.from_wei(base_fee, "gwei"))
            priority_gwei = (
                float(self.web3.from_wei(priority_fee, "gwei")) if priority_fee else 0.0
            )
            gas_price_gwei = base_fee_gwei + priority_gwei
        try:
            client_version = self.web3.w3.client_version
            client_version = await client_version if asyncio.iscoroutine(client_version) else client_version
        except Exception:
            client_version = None
        info = {
            "chain_id": chain_id,
            "rpc_url": getattr(self.web3, "current_rpc_url", None),
            "client_version": client_version,
            "latest_block_number": block_number,
            "latest_block_timestamp": block_time,
        }
        if base_fee is not None:
            info["base_fee_per_gas_gwei"] = float(self.web3.from_wei(base_fee, "gwei"))
        if priority_fee is not None:
            info["max_priority_fee_per_gas_gwei"] = float(
                self.web3.from_wei(priority_fee, "gwei")
            )
        if gas_price_gwei is not None:
            info["estimated_gas_price_gwei"] = gas_price_gwei
        self.context.update_state("provider_status", info)
        await self.context.append_to_history(
            "system",
            f"Provider status refreshed (chain_id={chain_id}, block={block_number})",
        )
        return info

    async def inspect_contract(self, address: str) -> Dict[str, Any]:
        if not self.web3.is_address(address):
            raise WalletError("Invalid contract address.")
        checksum = Web3.to_checksum_address(address)
        await self.web3.ensure_connection()
        code = await self.web3.get_code(checksum)
        is_contract = bool(code and code != b"\x00")
        balance_wei = await self.web3.get_balance(checksum)
        result: Dict[str, Any] = {
            "address": checksum,
            "is_contract": is_contract,
            "balance_eth": float(self.web3.from_wei(balance_wei, "ether")),
            "bytecode_length": len(code or b"") if code else 0,
        }
        if not is_contract:
            return result
        result["bytecode_hash"] = Web3.keccak(code).hex()
        metadata: Dict[str, Any] = {}
        for field in ("symbol", "name", "decimals"):
            try:
                value = await self.web3.call_contract_function(
                    checksum, _ERC20_METADATA_ABI, field
                )
                metadata[field] = value
            except Exception:
                continue
        if metadata:
            result["erc20_metadata"] = metadata
        return result
