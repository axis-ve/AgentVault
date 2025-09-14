import os
from typing import Optional

import httpx

from ..core import ContextSchema


class OllamaAdapter:
    """Minimal async adapter for a local Ollama server.

    Uses the /api/chat endpoint. Configure with OLLAMA_HOST and OLLAMA_MODEL.
    """

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    async def call(self, context: ContextSchema) -> str:
        msgs = []
        if context.system_prompt:
            msgs.append({"role": "system", "content": context.system_prompt})
        msgs.extend(context.history)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.host}/api/chat",
                    json={"model": self.model, "messages": msgs, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
                # Ollama returns {message: {role, content}}
                msg = data.get("message", {}).get("content")
                return msg or ""
        except Exception as e:
            return f"[Ollama error: {e}]"

