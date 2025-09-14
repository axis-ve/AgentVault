import os
import logging
from typing import Any, Dict, List, Optional, Literal

import structlog
import tiktoken
from pydantic import BaseModel, Field, field_validator

from . import MCPError, ContextOverflowError


# Configure stdlib logging level from env before structlog setup
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, _log_level, logging.INFO))


# Structured logging setup
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("agentvault_mcp")


class ContextSchema(BaseModel):
    """MCP Protocol Schema: Validates and structures context."""

    history: List[Dict[str, str]] = Field(
        default_factory=list, description="Conversation history."
    )
    system_prompt: str = Field(
        default="", description="System-level instructions."
    )
    state: Dict[str, Any] = Field(
        default_factory=dict, description="Persistent state (e.g., wallet info)."
    )
    # Context budget (approx) for prompt + history
    max_tokens: int = Field(default=4096, gt=0, description="Context token budget.")
    # Completion budget for the model's reply
    completion_max_tokens: int = Field(
        default=512, gt=0, description="Max tokens for model completion."
    )
    trim_strategy: Literal["recency", "semantic"] = Field(
        default="recency", description="Trimming method."
    )

    @field_validator("history")
    def validate_history(cls, v):
        for msg in v:
            if "role" not in msg or "content" not in msg:
                raise ValueError("History messages must have 'role' and 'content'.")
        return v


class ContextManager:
    """Core MCP: Manages context with trimming and state injection."""

    def __init__(
        self,
        max_tokens: int = 4096,
        trim_strategy: str = "recency",
        encoding_name: str = "o200k_base",  # Recommended for GPT-4o
        logger: structlog.stdlib.BoundLogger = logger,
    ):
        self.schema = ContextSchema(max_tokens=max_tokens, trim_strategy=trim_strategy)
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.logger = logger.bind(component="ContextManager")
        self.adapters: Dict[str, Any] = {}

    def register_adapter(self, name: str, adapter: Any):
        """Dependency injection for adapters."""
        self.adapters[name] = adapter
        self.logger.info("Adapter registered", name=name)

    async def append_to_history(self, role: str, content: str) -> None:
        """Append message and trim if needed."""
        self.schema.history.append({"role": role, "content": content})
        await self._trim_context()

    async def _trim_context(self) -> None:
        """Apply trimming strategy atomically."""
        token_count = self._calculate_tokens()
        if token_count > self.schema.max_tokens * 0.9:  # Proactive trim
            if self.schema.trim_strategy == "recency":
                while (
                    token_count > self.schema.max_tokens * 0.8
                    and len(self.schema.history) > 1
                ):
                    removed = self.schema.history.pop(0)
                    token_count = self._calculate_tokens()
                    self.logger.debug("Trimmed message", removed=removed["role"])
            else:  # Semantic: Placeholder for embeddings (implement with sentence-transformers in extension)
                if not getattr(self, "_semantic_trim_warned", False):
                    self.logger.warning(
                        "Semantic trim requested but not implemented in base"
                    )
                    self._semantic_trim_warned = True
                # For production, integrate FAISS here with pre-computed embeddings
            if self._calculate_tokens() > self.schema.max_tokens:
                raise ContextOverflowError(
                    f"Context overflow after trim: {self._calculate_tokens()} tokens"
                )

    def _calculate_tokens(self) -> int:
        sys_tokens = len(self.encoding.encode(self.schema.system_prompt))
        hist_tokens = sum(
            len(self.encoding.encode(msg["content"])) for msg in self.schema.history
        )
        return sys_tokens + hist_tokens + len(self.schema.state) * 10  # Rough state overhead

    async def generate_response(
        self, user_message: str, adapter_name: str = "openai"
    ) -> str:
        """Full cycle: Append, call adapter, append response."""
        if adapter_name not in self.adapters:
            raise MCPError(f"Adapter {adapter_name} not registered")

        await self.append_to_history("user", user_message)
        adapter = self.adapters[adapter_name]
        reply = await adapter.call(self.schema)
        await self.append_to_history("assistant", reply)
        self.logger.info("Response generated", tokens=self._calculate_tokens())
        return reply

    def update_state(self, key: str, value: Any) -> None:
        """Inject state (e.g., wallet info) into schema."""
        self.schema.state[key] = value
        self.logger.debug("State updated", key=key)

