"""Configuration utilities extracted from server.py and cli.py to eliminate duplication."""

import os
from cryptography.fernet import Fernet, InvalidToken
from .core import logger

# Configuration constants
DEFAULT_RPC_URL = "https://ethereum-sepolia.publicnode.com"
DEFAULT_STORE_PATH = "agentvault_store.json"
KEY_FILE_PERMISSIONS = 0o600
RECEIPT_TIMEOUT_SECONDS = 120
MAX_BACKOFF_DELAY = 2.0
CONTEXT_TRIM_THRESHOLD = 0.9
CONTEXT_TRIM_TARGET = 0.8
DEFAULT_MAX_TOKENS = 4096
DEFAULT_COMPLETION_TOKENS = 512
DEFAULT_RATE_LIMIT_CALLS = 120
DEFAULT_RATE_LIMIT_WINDOW = 60


def get_rpc_url() -> str:
    """Get RPC URL with proper fallback chain.

    Priority order:
    1. WEB3_RPC_URL environment variable
    2. ALCHEMY_HTTP_URL environment variable
    3. Auto-generated Alchemy URL from ALCHEMY_API_KEY + ALCHEMY_NETWORK
    4. Default public Sepolia endpoint
    """
    # Check explicit environment variables first
    rpc_url = os.getenv("WEB3_RPC_URL") or os.getenv("ALCHEMY_HTTP_URL")
    if rpc_url:
        return rpc_url

    # Try to build Alchemy URL from API key and network
    alchemy_url = _build_alchemy_url()
    if alchemy_url:
        return alchemy_url

    # Fall back to default public endpoint
    return DEFAULT_RPC_URL


def _build_alchemy_url() -> str | None:
    """Build Alchemy HTTP URL from environment variables."""
    api_key = os.getenv("ALCHEMY_API_KEY")
    if not api_key:
        return None

    network = os.getenv("ALCHEMY_NETWORK", "sepolia").strip()
    return f"https://eth-{network}.g.alchemy.com/v2/{api_key}"


def get_or_create_encrypt_key() -> str:
    """Get encryption key or create/persist one if not provided.

    Returns:
        Valid Fernet encryption key as string

    Raises:
        RuntimeError: If provided key is invalid and no fallback available
    """
    encrypt_key = os.getenv("ENCRYPT_KEY")
    store_path = os.getenv("AGENTVAULT_STORE", DEFAULT_STORE_PATH)
    key_path = os.path.splitext(store_path)[0] + ".key"

    if not encrypt_key:
        return _load_or_create_key_file(key_path)

    # Validate provided key
    if _validate_encrypt_key(encrypt_key):
        return encrypt_key

    # Fall back to key file or generate new one
    logger.warning("Invalid ENCRYPT_KEY provided; falling back to key file or generated key")
    return _load_or_create_key_file(key_path)


def _load_or_create_key_file(key_path: str) -> str:
    """Load existing key file or create a new one."""
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key_data = f.read().decode()
            if _validate_encrypt_key(key_data):
                return key_data
            logger.warning(f"Invalid key file {key_path}, generating new key")

    # Generate and save new key
    new_key = Fernet.generate_key().decode()
    try:
        with open(key_path, "wb") as f:
            f.write(new_key.encode())
        os.chmod(key_path, KEY_FILE_PERMISSIONS)
        logger.info(f"Generated new encryption key: {key_path}")
    except Exception as e:
        logger.warning(f"Failed to save encryption key file: {e}")

    return new_key


def _validate_encrypt_key(key: str) -> bool:
    """Validate that a string is a valid Fernet key."""
    try:
        Fernet(key.encode())
        return True
    except (InvalidToken, ValueError):
        return False




def get_context_config() -> dict:
    """Get context management configuration."""
    return {
        "max_tokens": int(os.getenv("MCP_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        "completion_max_tokens": DEFAULT_COMPLETION_TOKENS,
        "trim_threshold": CONTEXT_TRIM_THRESHOLD,
        "trim_target": CONTEXT_TRIM_TARGET,
    }


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    return os.getenv("VAULTPILOT_DATABASE_URL", "sqlite+aiosqlite:///vaultpilot.db")


def get_policy_path() -> str:
    """Get policy configuration file path."""
    return os.getenv("VAULTPILOT_POLICY_PATH", "vaultpilot_policy.yml")


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from environment."""
    return os.getenv("OPENAI_API_KEY")


def get_openai_model() -> str:
    """Get OpenAI model name from environment."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_ollama_config() -> tuple[str, str]:
    """Get Ollama host and model configuration."""
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    return host, model


def get_log_level() -> str:
    """Get logging level from environment."""
    return os.getenv("LOG_LEVEL", "INFO").upper()


def get_admin_api_config() -> dict:
    """Get admin API server configuration."""
    return {
        "host": os.getenv("ADMIN_API_HOST", "127.0.0.1"),
        "port": int(os.getenv("ADMIN_API_PORT", "9900")),
        "log_level": os.getenv("ADMIN_API_LOG_LEVEL", "info"),
        "reload": os.getenv("ADMIN_API_RELOAD", "false").lower() == "true",
    }


def get_rate_limit_config() -> dict:
    """Get rate limiting configuration."""
    return {
        "calls": int(os.getenv("RATE_LIMIT_CALLS", DEFAULT_RATE_LIMIT_CALLS)),
        "window": int(os.getenv("RATE_LIMIT_WINDOW", DEFAULT_RATE_LIMIT_WINDOW)),
    }


def get_wallet_config() -> dict:
    """Get wallet-specific configuration."""
    return {
        "max_transaction_eth": get_max_transaction_eth(),
        "confirmation_code": get_confirmation_code(),
        "export_confirmation_code": get_export_confirmation_code(),
        "allow_plaintext_export": should_allow_plaintext_export(),
        "faucet_url": get_faucet_url(),
        "store_path": os.getenv("AGENTVAULT_STORE", DEFAULT_STORE_PATH),
    }


def get_ui_config() -> dict:
    """Get UI generation configuration."""
    return {
        "qr_size": int(os.getenv("QR_SIZE", "256")),
        "qr_border": int(os.getenv("QR_BORDER", "4")),
        "dashboard_refresh_seconds": int(os.getenv("DASHBOARD_REFRESH_SECONDS", "30")),
    }


def get_max_transaction_eth() -> float | None:
    """Get maximum transaction amount requiring confirmation."""
    max_tx_env = os.getenv("AGENTVAULT_MAX_TX_ETH")
    if not max_tx_env:
        return None
    try:
        return float(max_tx_env)
    except ValueError:
        logger.warning(f"Invalid AGENTVAULT_MAX_TX_ETH value: {max_tx_env}")
        return None


def get_confirmation_code() -> str | None:
    """Get transaction confirmation code."""
    return os.getenv("AGENTVAULT_TX_CONFIRM_CODE")


def get_export_confirmation_code() -> str | None:
    """Get export confirmation code."""
    return os.getenv("AGENTVAULT_EXPORT_CODE")


def should_allow_plaintext_export() -> bool:
    """Check if plaintext key export is allowed."""
    return os.getenv("AGENTVAULT_ALLOW_PLAINTEXT_EXPORT") == "1"


def get_faucet_url() -> str | None:
    """Get faucet endpoint URL."""
    return os.getenv("AGENTVAULT_FAUCET_URL")