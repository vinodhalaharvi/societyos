"""
Async client for the Qwen Cloud API.

Qwen Cloud uses the OpenAI-compatible REST API, so we use the `openai` Python
package pointed at Alibaba's endpoint.

Usage:
    from societyos.qwen_client import chat, stream_chat

    # Simple single response
    reply = await chat(messages=[{"role": "user", "content": "Hello"}])

    # Streaming (yields text chunks)
    async for chunk in stream_chat(messages=[...]):
        print(chunk, end="", flush=True)
"""

from __future__ import annotations
from collections.abc import AsyncIterator
from openai import AsyncOpenAI
from .settings import settings


def _client() -> AsyncOpenAI:
    """Build a fresh OpenAI-compatible client pointed at Qwen Cloud."""
    return AsyncOpenAI(
        api_key=settings.qwen_api_key,
        base_url=settings.qwen_base_url,
    )


async def chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    Send a list of messages and return the assistant's reply as a string.

    Args:
        messages: OpenAI-format message list, e.g.
                  [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        model:    Override the default model from settings.
        temperature: 0.0 = deterministic, 1.0 = creative.
        max_tokens: Maximum tokens in the reply.

    Returns:
        The assistant's text reply.
    """
    client = _client()
    response = await client.chat.completions.create(
        model=model or settings.qwen_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def stream_chat(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """
    Stream the assistant's reply token by token.

    Usage:
        async for chunk in stream_chat(messages):
            print(chunk, end="", flush=True)
    """
    client = _client()
    stream = await client.chat.completions.create(
        model=model or settings.qwen_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
