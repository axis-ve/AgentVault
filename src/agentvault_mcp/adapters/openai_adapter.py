import os
from typing import Optional

from openai import AsyncOpenAI

from ..core import ContextSchema


class OpenAIAdapter:
    """Adapter for OpenAI LLM calls (async)."""

    def __init__(self, api_key: str, model: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def call(self, context: ContextSchema) -> str:
        messages = [{"role": "system", "content": context.system_prompt}] + context.history
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=context.completion_max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content

