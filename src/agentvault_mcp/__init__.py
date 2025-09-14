__all__ = [
    "MCPError",
    "ContextOverflowError",
    "WalletError",
]

class MCPError(Exception):
    """Base exception for MCP operations."""
    pass


class ContextOverflowError(MCPError):
    """Raised when context exceeds token limits after trimming."""
    pass


class WalletError(MCPError):
    """Raised for wallet-specific issues."""
    pass

