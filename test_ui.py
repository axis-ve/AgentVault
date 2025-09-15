import pytest
try:
    import segno  # type: ignore
    _HAS_SEGNO = True
except Exception:
    _HAS_SEGNO = False

from agentvault_mcp.ui import tipjar_page_html, eth_uri, dashboard_html


@pytest.mark.skipif(not _HAS_SEGNO, reason="segno not installed; UI tests optional")
def test_tipjar_page_html_contains_svg_and_uri():
    html = tipjar_page_html("0x" + "1" * 40, 0.01)
    assert "ethereum:" in html
    assert "<svg" in html
    assert "Toggle Theme" in html
    assert "Copy" in html


@pytest.mark.skipif(not _HAS_SEGNO, reason="segno not installed; UI tests optional")
def test_dashboard_html_contains_sections():
    wallets = [
        {"agent_id": "a", "address": "0x" + "1" * 40, "balance_eth": 0.0},
        {"agent_id": "b", "address": "0x" + "2" * 40, "balance_eth": 1.23},
    ]
    strategies = {
        "s1": {
            "agent_id": "a",
            "to_address": "0x" + "3" * 40,
            "amount_eth": 0.1,
            "interval_seconds": 60,
            "enabled": True,
        }
    }
    html = dashboard_html(wallets, strategies)
    assert "Wallets" in html and "Strategies" in html
    assert "0x" in html
    assert "Toggle Theme" in html
    assert "Copy" in html
import os
import sys

# Allow running tests directly via `python test_ui.py` without installing pkg
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
