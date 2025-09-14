from __future__ import annotations

import os
from typing import Optional

import segno


def eth_payment_uri(address: str, amount_eth: Optional[float] = None) -> str:
    """Build an EIP-681-ish payment URI.

    Uses decimal wei for value if amount provided.
    """
    addr = address
    if amount_eth is None:
        return f"ethereum:{addr}"
    wei = int(amount_eth * 10**18)
    return f"ethereum:{addr}?value={wei}"


def generate_tipjar_qr(
    address: str, out_path: str, amount_eth: Optional[float] = None
) -> str:
    """Generate a QR PNG for an ETH payment URI and save to out_path.

    Returns the output path.
    """
    uri = eth_payment_uri(address, amount_eth)
    qr = segno.make(uri, micro=False)
    qr.save(out_path, scale=5, border=2)
    return out_path

