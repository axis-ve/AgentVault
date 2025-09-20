import asyncio
import os
import random
from typing import Any, Callable, Optional

from web3 import AsyncWeb3
from web3.exceptions import Web3Exception


class Web3Adapter:
    """Adapter for Ethereum interactions with basic retry and RPC rotation."""

    def __init__(self, rpc_url: str):
        # Gather URLs from explicit arg, optional Alchemy URLs, and fallbacks
        urls_env = [u.strip() for u in os.getenv("WEB3_RPC_URLS", "").split(",") if u.strip()]
        alchemy_http = os.getenv("ALCHEMY_HTTP_URL")
        alchemy_ws = os.getenv("ALCHEMY_WS_URL")
        urls: list[str] = []
        if rpc_url:
            urls.append(rpc_url)
        if alchemy_http:
            urls.append(alchemy_http)
        if alchemy_ws:
            urls.append(alchemy_ws)
        urls.extend(urls_env)
        # Deduplicate preserving order
        seen = set()
        urls = [u for u in urls if not (u in seen or seen.add(u))]
        if not urls:
            raise RuntimeError("No RPC URLs provided")
        self._urls = urls
        self._idx = 0
        self._current_url = self._urls[self._idx]
        self.w3 = AsyncWeb3(self._make_provider(self._current_url))

    def _make_provider(self, url: str):
        if url.startswith("ws://") or url.startswith("wss://"):
            return AsyncWeb3.AsyncWebsocketProvider(url)
        return AsyncWeb3.AsyncHTTPProvider(url)

    def _rotate(self) -> None:
        self._idx = (self._idx + 1) % len(self._urls)
        self._current_url = self._urls[self._idx]
        self.w3 = AsyncWeb3(self._make_provider(self._current_url))

    @property
    def current_rpc_url(self) -> str:
        return self._current_url

    async def ensure_connection(self) -> bool:
        # Try all providers until one connects
        for _ in range(len(self._urls)):
            try:
                if await self.w3.is_connected():
                    return True
            except Exception:
                pass
            self._rotate()
        raise RuntimeError("Failed to connect to any RPC")

    async def _call(self, func: Callable[[], Any], *, attempts: int = 3) -> Any:
        delay = 0.25
        last_err: Optional[Exception] = None
        for _ in range(attempts * len(self._urls)):
            try:
                res = func()
                if asyncio.iscoroutine(res):
                    return await res
                return res
            except (Web3Exception, Exception) as e:  # rotate and retry
                last_err = e
                self._rotate()
                await asyncio.sleep(delay + random.random() * 0.25)
                delay = min(delay * 2, 2.0)
        if last_err:
            raise last_err
        raise RuntimeError("RPC call failed")

    # Convenience wrappers with retry/rotation
    async def get_nonce(self, address: str) -> int:
        return await self._call(lambda: self.w3.eth.get_transaction_count(address))

    async def get_block_latest(self) -> dict:
        return await self._call(lambda: self.w3.eth.get_block("latest"))

    async def max_priority_fee(self) -> int:
        async def _fetch():
            return await self.w3.eth.max_priority_fee

        return await self._call(_fetch)

    async def estimate_gas(self, txn: dict) -> int:
        return await self._call(lambda: self.w3.eth.estimate_gas(txn))

    async def send_raw_transaction(self, raw: bytes) -> Any:
        return await self._call(lambda: self.w3.eth.send_raw_transaction(raw))

    async def wait_for_receipt(self, tx_hash: Any, timeout: int = 120) -> Any:
        return await self._call(lambda: self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout))

    async def get_balance(self, address: str) -> int:
        return await self._call(lambda: self.w3.eth.get_balance(address))

    async def get_code(self, address: str) -> bytes:
        return await self._call(lambda: self.w3.eth.get_code(address))

    async def call_contract_function(
        self, address: str, abi: list[dict[str, Any]], method: str, *args: Any
    ) -> Any:
        contract = self.w3.eth.contract(address=address, abi=abi)
        func = getattr(contract.functions, method)(*args)
        return await self._call(lambda: func.call())

    # Pure helpers
    def to_wei(self, v: float, unit: str) -> int:
        return self.w3.to_wei(v, unit)

    def from_wei(self, v: int, unit: str) -> float:
        return float(self.w3.from_wei(v, unit))

    def is_address(self, addr: str) -> bool:
        return self.w3.is_address(addr)
