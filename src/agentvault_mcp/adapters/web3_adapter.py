from web3 import AsyncWeb3


class Web3Adapter:
    """Adapter for Ethereum interactions (async)."""

    def __init__(self, rpc_url: str):
        self.w3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))

    async def ensure_connection(self) -> bool:
        if await self.w3.is_connected():
            return True
        raise RuntimeError("Failed to connect to RPC")

    async def get_nonce(self, address: str) -> int:
        return await self.w3.eth.get_transaction_count(address)

