import asyncio

from cryptography.fernet import Fernet

from agentvault_mcp.core import ContextManager
from agentvault_mcp.wallet import AgentWalletManager


class _Web3AdapterStub:
    class _W3:
        class eth:
            chain_id = 11155111

            @staticmethod
            async def get_block(identifier):
                return {"baseFeePerGas": 0}

        def to_wei(self, v, unit):
            return int(v * 10**18)

        def from_wei(self, v, unit):
            return v / 10**18

    def __init__(self):
        self.w3 = self._W3()

    async def ensure_connection(self):
        return True

    async def get_balance(self, *_):
        return 10**21

    async def estimate_gas(self, *_):
        return 21_000

    async def max_priority_fee(self):
        return 1_000_000_000

    async def get_block_latest(self):
        return {"baseFeePerGas": 1_000_000_000}

    async def get_nonce(self, *_):
        return 0

    async def send_raw_transaction(self, *_):
        return b""

    async def wait_for_receipt(self, *_ , timeout=120):
        return type("R", (), {"status": 1})()

    def is_address(self, a):
        return True


def _make_manager(tmp_path):
    ctx = ContextManager()
    key = Fernet.generate_key().decode()
    return AgentWalletManager(ctx, _Web3AdapterStub(), key, persist_path=str(tmp_path / "store.json"))


def test_import_private_key_and_sign(tmp_path):
    async def runner():
        mgr = _make_manager(tmp_path)
        priv = "0xfb4222fce02fa5e3d33ec08294b5fbeee428028532133116ff1d84fe8be9719f"
        address = await mgr.import_wallet_from_private_key("imported", priv)
        assert address == "0xC4504EE5091e093499a0586Ca7525A0F20520747"

        sign = await mgr.sign_message("imported", "hello")
        verify = await mgr.verify_message(address, "hello", sign["signature"])
        assert verify["valid"]

    asyncio.run(runner())


def test_encrypt_and_decrypt_keystore(tmp_path):
    async def runner():
        mgr = _make_manager(tmp_path)
        priv = "0xfb4222fce02fa5e3d33ec08294b5fbeee428028532133116ff1d84fe8be9719f"
        await mgr.import_wallet_from_private_key("imported", priv)
        encrypted = await mgr.encrypt_wallet_json("imported", "pass123")
        data = await mgr.decrypt_wallet_json(encrypted, "pass123")
        assert data["address"].lower() == "0xc4504ee5091e093499a0586ca7525a0f20520747".lower()
        assert data["private_key"].lower() == priv.lower()

    asyncio.run(runner())


def test_sign_typed_data(tmp_path):
    async def runner():
        mgr = _make_manager(tmp_path)
        priv = "0xfb4222fce02fa5e3d33ec08294b5fbeee428028532133116ff1d84fe8be9719f"
        address = await mgr.import_wallet_from_private_key("imported", priv)

        typed_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Person": [
                    {"name": "name", "type": "string"},
                    {"name": "wallet", "type": "address"},
                ],
                "Mail": [
                    {"name": "from", "type": "Person"},
                    {"name": "to", "type": "Person"},
                    {"name": "contents", "type": "string"},
                ],
            },
            "primaryType": "Mail",
            "domain": {
                "name": "Ether Mail",
                "version": "1",
                "chainId": 11155111,
                "verifyingContract": "0xCcCCccccCCCCcCCCCCCcCcCccCcCCCcCcccccccC",
            },
            "message": {
                "from": {
                    "name": "Alice",
                    "wallet": address,
                },
                "to": {
                    "name": "Bob",
                    "wallet": "0xbBbBBBBbbBBBbbbBbbBbbbbBBbBbbbbBbBbbBBbB",
                },
                "contents": "Hello, Bob!",
            },
        }

        signed = await mgr.sign_typed_data("imported", typed_data)
        result = await mgr.verify_typed_data(address, typed_data, signed["signature"])
        assert result["valid"]

    asyncio.run(runner())


def test_generate_mnemonic(tmp_path):
    async def runner():
        mgr = _make_manager(tmp_path)
        phrase = await mgr.generate_mnemonic()
        assert isinstance(phrase, str)
        assert len(phrase.split()) == 12

    asyncio.run(runner())
