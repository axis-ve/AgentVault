from agentvault_mcp.ui import tipjar_page_html, eth_uri, dashboard_html


def test_tipjar_page_html_contains_svg_and_uri():
    html = tipjar_page_html("0x" + "1" * 40, 0.01)
    assert "ethereum:" in html
    assert "<svg" in html
    assert "Toggle Theme" in html
    assert "Copy" in html


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
