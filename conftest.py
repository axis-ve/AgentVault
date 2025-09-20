pytest_plugins = ("pytest_asyncio.plugin",)

import pytest

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
