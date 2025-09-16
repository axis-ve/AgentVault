"""Dynamic chain configuration helpers for DeFi integrations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

import httpx


@dataclass
class ChainConfig:
    chain_id: int
    name: str
    tokens: Dict[str, str]
    swap_mode: str  # e.g. "legacy_v3" or "universal_router"
    uniswap: Dict[str, Any]
    aave: Dict[str, Any]


class ConfigError(RuntimeError):
    pass


def load_chain_config(chain_id: int) -> ChainConfig:
    if chain_id == 11155111:
        return _load_sepolia()
    if chain_id == 1:
        return ChainConfig(
            chain_id=1,
            name="ethereum",
            tokens={
                "ETH": "0x0000000000000000000000000000000000000000",
                "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "USDC": "0xA0b86991C6218b36c1d19D4a2e9Eb0cE3606eB48",
                "USDT": "0xdAC17F958D2ee523a2206206994597C13d831ec7",
                "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            },
            swap_mode="legacy_v3",
            uniswap={
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "position_manager": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
            },
            aave={
                "pool": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2",
                "data_provider": "0x7B4EB56E7CD4b454BA8ff71E4518426369a138a3",
            },
        )
    if chain_id == 8453:  # Base
        return ChainConfig(
            chain_id=8453,
            name="base",
            tokens={"ETH": "0x0000000000000000000000000000000000000000"},
            swap_mode="legacy_v3",
            uniswap={
                "factory": "0x4752b94f3703f0A86dAFc7432Ba4fC0158845fE0",
                "router": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
                "position_manager": "0x883164536E9119eC416E44F04E8257f0dE4C595F",
                "quoter": None,
            },
            aave={},
        )
    if chain_id == 42161:
        return ChainConfig(
            chain_id=42161,
            name="arbitrum",
            tokens={"ETH": "0x0000000000000000000000000000000000000000"},
            swap_mode="legacy_v3",
            uniswap={
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "position_manager": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
            },
            aave={},
        )
    raise ConfigError(f"Unsupported chain_id: {chain_id}")


def _load_text(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        raise ConfigError(f"Failed to fetch {url}: {exc}") from exc
    if resp.status_code != 200:
        raise ConfigError(f"Failed to fetch {url}: HTTP {resp.status_code}")
    return resp.text


@lru_cache()
def _load_sepolia() -> ChainConfig:
    deploy_params = _parse_uniswap_sepolia()
    aave_params = _parse_aave_sepolia()
    tokens = {
        "ETH": "0x0000000000000000000000000000000000000000",
        "WETH": deploy_params["weth"],
        "USDC": "0x94a9D9AC8a22534E3FaCa9F4e7F2E2cf85d5E4C8",
        "LINK": "0xf8Fb3713D459D7C1018BD0A49D19b4C44290EBE5",
        "DAI": "0xFF34B3d4Aee8ddCd6F9AFFFB6Fe49bD371b8a357",
    }
    return ChainConfig(
        chain_id=11155111,
        name="sepolia",
        tokens=tokens,
        swap_mode="universal_router",
        uniswap={
            "factory": deploy_params["v3_factory"],
            "v2_factory": deploy_params["v2_factory"],
            "pool_init_code_hash": deploy_params["pool_init_code_hash"],
            "universal_router": deploy_params["universal_router"],
            "permit2": deploy_params["permit2"],
            "position_manager": deploy_params["v3_position_manager"],
            "default_fee": 3000,
        },
        aave={
            "pool": aave_params.get("POOL"),
            "data_provider": aave_params.get("AAVE_PROTOCOL_DATA_PROVIDER"),
        },
    )


def _parse_uniswap_sepolia() -> Dict[str, str]:
    text = _load_text(
        "https://raw.githubusercontent.com/Uniswap/universal-router/main/script/deployParameters/DeploySepolia.s.sol"
    )
    addresses = {
        "permit2": _extract(text, r"permit2:\s*(0x[0-9a-fA-F]+)"),
        "weth": _extract(text, r"weth9:\s*(0x[0-9a-fA-F]+)"),
        "v2_factory": _extract(text, r"v2Factory:\s*(0x[0-9a-fA-F]+)"),
        "v3_factory": _extract(text, r"v3Factory:\s*(0x[0-9a-fA-F]+)"),
        "pool_init_code_hash": _extract(text, r"poolInitCodeHash:\s*(0x[0-9a-fA-F]+)"),
        "v3_position_manager": _extract(text, r"v3NFTPositionManager:\s*(0x[0-9a-fA-F]+)"),
        "v4_pool_manager": _extract(text, r"v4PoolManager:\s*(0x[0-9a-fA-F]+)"),
        "v4_position_manager": _extract(text, r"v4PositionManager:\s*(0x[0-9a-fA-F]+)"),
    }
    deploy_json = json.loads(
        _load_text("https://raw.githubusercontent.com/Uniswap/universal-router/main/deploy-addresses/sepolia.json")
    )
    addresses["universal_router"] = deploy_json["UniversalRouterV1_2_V2Support"]
    return addresses


def _parse_aave_sepolia() -> Dict[str, str]:
    text = _load_text(
        "https://raw.githubusercontent.com/aave/aave-address-book/main/src/ts/AaveV3Sepolia.ts"
    )
    matches = re.findall(r"export const (\w+) = '([^']+)'", text)
    return {key: value for key, value in matches}


def _extract(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise ConfigError(f"Failed to find pattern {pattern}")
    return match.group(1)
