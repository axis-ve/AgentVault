import pytest
from httpx import AsyncClient
from wallet_mcp_server import app  # Import to test

@pytest.mark.asyncio
async def test_chat_autonomy():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/chat", json={"message": "Create a wallet"})
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert "Autonomously created wallet" in data["reply"]  # Checks generation