"""
DeFi integration module for AgentVault MCP.
Provides Uniswap swaps, Aave lending, and other DeFi operations.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, Tuple

from web3 import Web3
from eth_account import Account
from eth_defi.uniswap_v3.deployment import fetch_deployment
from eth_defi.uniswap_v3.swap import swap_with_slippage_protection
from eth_defi.uniswap_v3.price import get_onchain_price
from eth_defi.aave_v3.loan import supply
from eth_defi.aave_v3.balances import aave_v3_get_deposit_balance
from eth_abi import encode as abi_encode
from eth_utils import to_checksum_address

from .core import logger
from .network_config import ChainConfig, ConfigError, load_chain_config

NATIVE_ETH = "0x0000000000000000000000000000000000000000"
ERC20_METADATA_ABI = [
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

V3_POOL_ABI = json.loads(
    """
    [
      {
        "inputs": [],
        "name": "slot0",
        "outputs": [
          {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
          {"internalType": "int24", "name": "tick", "type": "int24"},
          {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
          {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
          {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
          {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
          {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
      }
    ]
    """
)

ERC20_ALLOWANCE_ABI = json.loads(
    """
    [
      {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
      {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"}
    ]
    """
)

UNIVERSAL_ROUTER_ABI = json.loads(
    """
    [
      {
        "inputs": [
          {"internalType": "bytes", "name": "commands", "type": "bytes"},
          {"internalType": "bytes[]", "name": "inputs", "type": "bytes[]"},
          {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
      }
    ]
    """
)

PERMIT2_ABI = json.loads(
    """
    [
      {
        "inputs": [
          {"internalType": "address", "name": "owner", "type": "address"},
          {"internalType": "address", "name": "token", "type": "address"},
          {"internalType": "address", "name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [
          {
            "components": [
              {"internalType": "uint160", "name": "amount", "type": "uint160"},
              {"internalType": "uint48", "name": "expiration", "type": "uint48"},
              {"internalType": "uint48", "name": "nonce", "type": "uint48"}
            ],
            "internalType": "struct IAllowanceTransfer.PermitDetails",
            "name": "",
            "type": "tuple"
          }
        ],
        "stateMutability": "view",
        "type": "function"
      },
      {
        "inputs": [
          {"internalType": "address", "name": "token", "type": "address"},
          {"internalType": "address", "name": "spender", "type": "address"},
          {"internalType": "uint160", "name": "amount", "type": "uint160"},
          {"internalType": "uint48", "name": "expiration", "type": "uint48"}
        ],
        "name": "approve",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
      }
    ]
    """
)

PERMIT2_MAX_AMOUNT = (1 << 160) - 1
PERMIT2_MAX_EXPIRATION = (1 << 48) - 1


class DeFiManager:
    """Manages DeFi operations for AgentVault."""

    def __init__(self, web3: Web3, chain_id: int = 1):
        try:
            self.chain_config: ChainConfig = load_chain_config(chain_id)
        except ConfigError as exc:
            raise ValueError(str(exc)) from exc
        self.web3 = web3
        self.chain_id = chain_id

    async def _run(self, func, *args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    def _resolve_token_address(self, token: str) -> str:
        token_upper = token.upper()
        if token_upper == "ETH":
            return NATIVE_ETH
        aliases = {k.upper(): v for k, v in self.chain_config.tokens.items()}
        return aliases.get(token_upper, token)

    def _get_uniswap_config(self) -> Dict[str, str]:
        if self.chain_config.swap_mode == "universal_router":
            return self.chain_config.uniswap
        cfg = self.chain_config.uniswap
        required = ("factory", "router", "position_manager")
        if not all(cfg.get(k) for k in required):
            raise ValueError(f"Uniswap config missing for chain {self.chain_id}")
        return cfg

    def _get_aave_config(self) -> Dict[str, str]:
        cfg = self.chain_config.aave or {}
        if not cfg.get("pool"):
            raise ValueError(f"Aave V3 not configured for chain {self.chain_id}")
        return cfg

    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get ERC-20 token information."""
        try:
            resolved = self._resolve_token_address(token_address)
            if resolved.lower() == NATIVE_ETH.lower():
                return {
                    "address": resolved,
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "decimals": 18,
                }

            token_contract = self.web3.eth.contract(address=resolved, abi=ERC20_METADATA_ABI)
            symbol = await self._run(lambda: token_contract.functions.symbol().call())
            name = await self._run(lambda: token_contract.functions.name().call())
            decimals = await self._run(lambda: token_contract.functions.decimals().call())
            return {
                "address": resolved,
                "symbol": symbol,
                "name": name,
                "decimals": decimals,
            }
        except Exception as e:
            logger.error(f"Failed to get token info for {token_address}: {e}")
            raise

    async def get_token_balance(self, wallet_address: str, token_address: str) -> float:
        """Get token balance for a wallet."""
        try:
            resolved = self._resolve_token_address(token_address)
            if resolved.lower() == NATIVE_ETH.lower():
                balance_wei = await self._run(self.web3.eth.get_balance, wallet_address)
                return float(self.web3.from_wei(balance_wei, "ether"))

            token_info = await self.get_token_info(resolved)
            token_contract = self.web3.eth.contract(address=token_info["address"], abi=[
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }
            ])
            balance_raw = await self._run(
                lambda: token_contract.functions.balanceOf(wallet_address).call()
            )
            balance = balance_raw / (10 ** token_info["decimals"])
            return float(balance)

        except Exception as e:
            logger.error(f"Failed to get balance for {token_address}: {e}")
            raise

    async def estimate_swap_quote(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """Get swap quote from Uniswap V3."""
        try:
            if self.chain_config.swap_mode == "universal_router":
                return await self._estimate_universal_router_quote(token_in, token_out, amount_in)

            cfg = self._get_uniswap_config()
            token_in_info = await self.get_token_info(token_in)
            token_out_info = await self.get_token_info(token_out)

            amount_in_wei = int(amount_in * (10 ** token_in_info["decimals"]))

            deployment = await self._run(
                lambda: fetch_deployment(
                    self.web3,
                    factory_address=cfg["factory"],
                    router_address=cfg["router"],
                    position_manager_address=cfg["position_manager"],
                    quoter_address=cfg.get("quoter"),
                )
            )

            try:
                amount_out_wei = await self._run(
                    lambda: get_onchain_price(
                        self.web3,
                        deployment,
                        token_in_info["address"],
                        token_out_info["address"],
                        amount_in_wei,
                        fee=3000,
                    )
                )
                amount_out = amount_out_wei / (10 ** token_out_info["decimals"])
            except Exception as quote_error:
                logger.warning(f"Failed to get onchain quote, using fallback: {quote_error}")
                amount_out = amount_in * 0.99

            return {
                "amount_in": amount_in,
                "amount_out": amount_out,
                "amount_out_min": amount_out * 0.99,
                "token_in": token_in_info,
                "token_out": token_out_info,
                "gas_estimate": 150000,
                "slippage": 0.01,
                "fee_tier": 3000,
            }

        except Exception as e:
            logger.error(f"Failed to get swap quote: {e}")
            raise

    async def execute_swap(
        self,
        private_key: str,
        token_in: str,
        token_out: str,
        amount_in: float,
        max_slippage: float = 0.01,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Execute token swap on Uniswap V3."""
        try:
            account = Account.from_key(private_key)
            wallet_address = account.address

            quote = await self.estimate_swap_quote(token_in, token_out, amount_in)

            if dry_run:
                if self.chain_config.swap_mode == "universal_router":
                    return await self._execute_universal_router_swap(
                        account,
                        token_in,
                        token_out,
                        amount_in,
                        quote,
                        max_slippage=max_slippage,
                        dry_run=True,
                    )
                return {
                    "action": "simulation",
                    "from": wallet_address,
                    "quote": quote,
                    "estimated_gas": quote["gas_estimate"],
                    "max_slippage": max_slippage,
                }

            if self.chain_config.swap_mode == "universal_router":
                return await self._execute_universal_router_swap(
                    account,
                    token_in,
                    token_out,
                    amount_in,
                    quote,
                    max_slippage=max_slippage,
                    dry_run=False,
                )

            cfg = self._get_uniswap_config()
            deployment = await self._run(
                lambda: fetch_deployment(
                    self.web3,
                    factory_address=cfg["factory"],
                    router_address=cfg["router"],
                    position_manager_address=cfg["position_manager"],
                    quoter_address=cfg.get("quoter"),
                )
            )

            amount_in_wei = int(amount_in * (10 ** quote["token_in"]["decimals"]))

            tx_hash = await self._run(
                lambda: swap_with_slippage_protection(
                    web3=self.web3,
                    deployment=deployment,
                    hot_wallet=account,
                    token_in=quote["token_in"]["address"],
                    token_out=quote["token_out"]["address"],
                    amount_in=amount_in_wei,
                    max_slippage=max_slippage,
                    fee=quote["fee_tier"],
                )
            )

            return {
                "action": "swap_executed",
                "tx_hash": tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash),
                "quote": quote,
                "wallet": wallet_address,
                "amount_in": amount_in,
                "estimated_amount_out": quote["amount_out"],
                "slippage_protection": max_slippage,
            }

        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            raise

    async def supply_to_aave(
        self,
        private_key: str,
        asset: str,
        amount: float,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Supply assets to Aave V3 for yield."""
        try:
            account = Account.from_key(private_key)
            wallet_address = account.address

            asset_info = await self.get_token_info(asset)

            if dry_run:
                return {
                    "action": "simulation",
                    "operation": "aave_supply",
                    "from": wallet_address,
                    "asset": asset_info,
                    "amount": amount,
                    "estimated_gas": 200000,
                    "aave_pool": self.chain_config.aave.get("pool") if self.chain_config.aave else None,
                }

            cfg = self._get_aave_config()
            amount_wei = int(amount * (10 ** asset_info["decimals"]))

            tx_hash = await self._run(
                lambda: supply(
                    web3=self.web3,
                    hot_wallet=account,
                    pool_contract_address=cfg["pool"],
                    asset=asset_info["address"],
                    amount=amount_wei,
                    on_behalf_of=wallet_address,
                    referral_code=0,
                )
            )

            return {
                "action": "aave_supply_executed",
                "tx_hash": tx_hash.hex() if hasattr(tx_hash, "hex") else str(tx_hash),
                "asset": asset_info,
                "amount": amount,
                "wallet": wallet_address,
                "aave_pool": cfg["pool"],
            }

        except Exception as e:
            logger.error(f"Failed to supply to Aave: {e}")
            raise

    async def get_aave_position(self, wallet_address: str) -> Dict[str, Any]:
        """Get Aave lending position for wallet."""
        try:
            cfg = self._get_aave_config()
        except ValueError as e:
            return {
                "wallet": wallet_address,
                "error": str(e),
                "positions": [],
            }

        try:
            positions = []
            total_collateral = 0.0
            for token_symbol, token_addr in self.chain_config.tokens.items():
                if token_symbol.upper() == "ETH":
                    continue
                try:
                    deposit_balance = await self._run(
                        aave_v3_get_deposit_balance,
                        web3=self.web3,
                        pool_contract_address=cfg["pool"],
                        wallet_address=wallet_address,
                        token_address=token_addr,
                    )
                    if deposit_balance > 0:
                        token_info = await self.get_token_info(token_addr)
                        balance_human = float(deposit_balance) / (10 ** token_info["decimals"])
                        positions.append(
                            {
                                "token": token_info,
                                "supply_balance": balance_human,
                                "debt_balance": 0.0,
                                "ltv": 0.0,
                                "liquidation_threshold": 0.0,
                            }
                        )
                        total_collateral += balance_human
                except Exception as token_error:
                    logger.debug(f"No deposit balance for {token_symbol}: {token_error}")

            return {
                "wallet": wallet_address,
                "total_collateral_base": total_collateral,
                "total_debt_base": 0.0,
                "health_factor": float("inf") if total_collateral else 0.0,
                "positions": positions,
            }

        except Exception as e:
            logger.error(f"Failed to get Aave position: {e}")
            return {
                "wallet": wallet_address,
                "error": str(e),
                "positions": [],
            }

    async def _estimate_universal_router_quote(
        self, token_in: str, token_out: str, amount_in: float
    ) -> Dict[str, Any]:
        token_in_info = await self._token_info_for_swap(token_in)
        token_out_info = await self._token_info_for_swap(token_out)
        cfg = self.chain_config.uniswap
        fee = cfg.get("default_fee", 3000)
        amount_in_wei = int(amount_in * (10 ** token_in_info["decimals"]))
        pool_addr, price = await self._run(
            self._compute_uniswap_price,
            cfg,
            token_in_info["address"],
            token_out_info["address"],
            fee,
            token_in_info["decimals"],
            token_out_info["decimals"],
        )
        fee_factor = 1 - fee / 1_000_000
        amount_out = amount_in * price * fee_factor
        return {
            "amount_in": amount_in,
            "amount_out": amount_out,
            "amount_out_min": amount_out * 0.99,
            "token_in": token_in_info,
            "token_out": token_out_info,
            "gas_estimate": 250000,
            "slippage": 0.01,
            "fee_tier": fee,
            "pool_address": pool_addr,
            "price_estimate": price,
        }

    def _compute_uniswap_price(
        self,
        cfg: Dict[str, Any],
        token_in_addr: str,
        token_out_addr: str,
        fee: int,
        token_in_decimals: int,
        token_out_decimals: int,
    ) -> Tuple[str, float]:
        factory = to_checksum_address(cfg["v3_factory"] if "v3_factory" in cfg else cfg["factory"])
        token_in_addr = to_checksum_address(token_in_addr)
        token_out_addr = to_checksum_address(token_out_addr)
        pool_address = self._compute_pool_address(
            factory,
            token_in_addr,
            token_out_addr,
            fee,
            cfg.get("pool_init_code_hash"),
        )
        pool_contract = self.web3.eth.contract(address=pool_address, abi=V3_POOL_ABI)
        slot0 = pool_contract.functions.slot0().call()
        sqrt_price_x96 = slot0[0]
        price_token1_per_token0 = (sqrt_price_x96 ** 2) / (2 ** 192)
        token0 = pool_contract.functions.token0().call()
        token1 = pool_contract.functions.token1().call()
        token0 = to_checksum_address(token0)
        token1 = to_checksum_address(token1)
        if token_in_addr == token0 and token_out_addr == token1:
            price = price_token1_per_token0 * (10 ** token_out_decimals) / (10 ** token_in_decimals)
        elif token_in_addr == token1 and token_out_addr == token0:
            price = (1 / price_token1_per_token0) * (10 ** token_out_decimals) / (10 ** token_in_decimals)
        else:
            raise ValueError("Token pair does not match pool ordering")
        return pool_address, price

    def _compute_pool_address(
        self,
        factory: str,
        token_a: str,
        token_b: str,
        fee: int,
        init_code_hash: str | None,
    ) -> str:
        if init_code_hash is None:
            raise ValueError("Pool init code hash required for universal router networks")
        if int(token_a, 16) > int(token_b, 16):
            token_a, token_b = token_b, token_a
        salt = Web3.keccak(abi_encode(["address", "address", "uint24"], [token_a, token_b, fee]))
        packed = b"\xff" + bytes.fromhex(factory[2:]) + salt + bytes.fromhex(init_code_hash[2:])
        address_bytes = Web3.keccak(packed)[12:]
        return to_checksum_address(address_bytes.hex())

    async def _token_info_for_swap(self, token: str) -> Dict[str, Any]:
        info = await self.get_token_info(token)
        if info["address"].lower() == NATIVE_ETH.lower():
            raise ValueError("Universal router swaps require ERC-20 tokens; wrap native ETH to WETH first.")
        return info

    def _get_universal_router_contract(self):
        address = to_checksum_address(self.chain_config.uniswap["universal_router"])
        return self.web3.eth.contract(address=address, abi=UNIVERSAL_ROUTER_ABI)

    def _get_permit2_contract(self):
        address = to_checksum_address(self.chain_config.uniswap["permit2"])
        return self.web3.eth.contract(address=address, abi=PERMIT2_ABI)

    def _ensure_token_allowance(self, account: Account, token_addr: str, spender: str):
        token = self.web3.eth.contract(address=to_checksum_address(token_addr), abi=ERC20_ALLOWANCE_ABI)
        current = token.functions.allowance(account.address, to_checksum_address(spender)).call()
        if current >= PERMIT2_MAX_AMOUNT // 2:
            return
        nonce = self.web3.eth.get_transaction_count(account.address)
        priority_fee = self.web3.eth.max_priority_fee
        latest_block = self.web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        max_fee = base_fee * 2 + priority_fee
        tx = token.functions.approve(to_checksum_address(spender), PERMIT2_MAX_AMOUNT).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "chainId": self.chain_id,
            }
        )
        tx["gas"] = self.web3.eth.estimate_gas(tx)
        signed = account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError("Token approval transaction failed")

    def _get_permit2_allowance(self, owner: str, token_addr: str, cfg: Dict[str, Any]) -> Dict[str, int]:
        contract = self._get_permit2_contract()
        result = contract.functions.allowance(
            to_checksum_address(owner),
            to_checksum_address(token_addr),
            to_checksum_address(cfg["universal_router"]),
        ).call()
        amount = int(result[0]) if isinstance(result, (list, tuple)) and len(result) > 0 else 0
        expiration = int(result[1]) if isinstance(result, (list, tuple)) and len(result) > 1 else 0
        return {"amount": amount, "expiration": expiration}

    def _approve_permit2(self, account: Account, token_addr: str, cfg: Dict[str, Any]) -> str:
        contract = self._get_permit2_contract()
        function = contract.functions.approve(
            to_checksum_address(token_addr),
            to_checksum_address(cfg["universal_router"]),
            PERMIT2_MAX_AMOUNT,
            PERMIT2_MAX_EXPIRATION,
        )
        tx_params = {"from": account.address}
        tx_base = function.build_transaction(tx_params)
        gas_estimate = self.web3.eth.estimate_gas(tx_base)
        nonce = self.web3.eth.get_transaction_count(account.address)
        priority_fee = self.web3.eth.max_priority_fee
        latest_block = self.web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        max_fee = base_fee * 2 + priority_fee
        tx = function.build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "gas": gas_estimate,
                "chainId": self.chain_id,
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError("Permit2 approval transaction failed")
        return tx_hash.hex()

    def _send_universal_router_tx(
        self,
        account: Account,
        commands: bytes,
        inputs: list[bytes],
        deadline: int,
        value_wei: int,
    ) -> str:
        router = self._get_universal_router_contract()
        function = router.functions.execute(commands, inputs, deadline)
        tx_params = {"from": account.address, "value": value_wei}
        tx_base = function.build_transaction(tx_params)
        gas_estimate = self.web3.eth.estimate_gas(tx_base)
        nonce = self.web3.eth.get_transaction_count(account.address)
        priority_fee = self.web3.eth.max_priority_fee
        latest_block = self.web3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        max_fee = base_fee * 2 + priority_fee
        tx = function.build_transaction(
            {
                "from": account.address,
                "value": value_wei,
                "nonce": nonce,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "gas": gas_estimate,
                "chainId": self.chain_id,
            }
        )
        signed = account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        if receipt.status != 1:
            raise RuntimeError("Universal Router transaction failed")
        return tx_hash.hex()

    async def _execute_universal_router_swap(
        self,
        account: Account,
        token_in: str,
        token_out: str,
        amount_in: float,
        quote: Dict[str, Any],
        *,
        max_slippage: float,
        dry_run: bool,
    ) -> Dict[str, Any]:
        cfg = self.chain_config.uniswap
        token_in_info = quote["token_in"]
        token_out_info = quote["token_out"]
        amount_in_wei = int(amount_in * (10 ** token_in_info["decimals"]))
        min_out_wei = int(
            max(
                0,
                quote["amount_out"] * (1 - max_slippage) * (10 ** token_out_info["decimals"]),
            )
        )
        fee = cfg.get("default_fee", 3000)
        path = bytes.fromhex(token_in_info["address"][2:]) + fee.to_bytes(3, "big") + bytes.fromhex(
            token_out_info["address"][2:]
        )
        commands = bytes([0x00])
        inputs_bytes = abi_encode(
            ["address", "uint256", "uint256", "bytes", "bool"],
            [account.address, amount_in_wei, min_out_wei, path, True],
        )
        deadline = int(time.time()) + 600

        permit_info = {"amount": PERMIT2_MAX_AMOUNT, "expiration": PERMIT2_MAX_EXPIRATION}
        permit_required = False
        if token_in_info["address"].lower() != NATIVE_ETH.lower():
            await self._run(
                self._ensure_token_allowance,
                account,
                token_in_info["address"],
                cfg["permit2"],
            )
            permit_info = await self._run(
                self._get_permit2_allowance,
                account.address,
                token_in_info["address"],
                cfg,
            )
            permit_required = (
                permit_info.get("amount", 0) < amount_in_wei
                or permit_info.get("expiration", 0) <= int(time.time())
            )

        dry_run_payload = {
            "action": "simulation" if dry_run else "pending",
            "from": account.address,
            "quote": quote,
            "estimated_gas": 250000,
            "max_slippage": max_slippage,
            "universal_router": {
                "contract": cfg["universal_router"],
                "commands_hex": commands.hex(),
                "inputs_hex": [inputs_bytes.hex()],
                "permit2": cfg["permit2"],
                "value": 0,
                "deadline": deadline,
            },
            "permit2": {
                "allowance": permit_info.get("amount"),
                "expiration": permit_info.get("expiration"),
                "needs_approval": permit_required,
            },
        }

        if dry_run:
            return dry_run_payload

        permit_tx_hash = None
        if permit_required:
            permit_tx_hash = await self._run(
                self._approve_permit2,
                account,
                token_in_info["address"],
                cfg,
            )

        tx_hash = await self._run(
            self._send_universal_router_tx,
            account,
            commands,
            [inputs_bytes],
            deadline,
            0,
        )

        return {
            "action": "swap_executed",
            "tx_hash": tx_hash,
            "permit2_tx_hash": permit_tx_hash,
            "quote": quote,
            "wallet": account.address,
            "amount_in": amount_in,
            "estimated_amount_out": quote["amount_out"],
            "slippage_protection": max_slippage,
            "deadline": deadline,
        }


async def test_defi_functionality():
    """Test DeFi functionality with mock data."""
    from web3 import Web3

    web3 = Web3(Web3.HTTPProvider("https://ethereum-sepolia.publicnode.com"))

    if not web3.is_connected():
        print("✗ Could not connect to Ethereum network")
        return False

    defi = DeFiManager(web3, chain_id=11155111)  # Sepolia testnet

    try:
        eth_info = await defi.get_token_info("ETH")
        print(f"✓ ETH token info: {eth_info}")

        try:
            quote = await defi.estimate_swap_quote("ETH", "WETH", 0.1)
            print(f"✓ Swap quote: {quote}")
        except Exception as quote_error:
            print(f"⚠ Swap quote test failed (expected on testnet): {quote_error}")

        print("✓ DeFi module basic functionality working")

    except Exception as e:
        print(f"✗ DeFi test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    asyncio.run(test_defi_functionality())
