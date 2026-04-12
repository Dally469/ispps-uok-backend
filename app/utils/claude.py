from __future__ import annotations

import anthropic

from app.config import get_settings

_client: anthropic.Anthropic | None = None

DEFAULT_SYSTEM = (
    "You are an educational AI assistant for the ISPPS "
    "(Intelligent Student Performance Prediction System). "
    "Provide concise, actionable insights about student academic performance."
)


def get_claude() -> anthropic.Anthropic:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise RuntimeError("Missing ANTHROPIC_API_KEY environment variable")
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def ask_claude(prompt: str, system_prompt: str | None = None) -> str:
    client = get_claude()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt or DEFAULT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    block = message.content[0]
    return block.text if block.type == "text" else ""


def stream_claude(prompt: str, messages: list[dict] | None = None, system_prompt: str | None = None):
    """Return a streaming iterator of text chunks."""
    client = get_claude()
    msgs = messages or [{"role": "user", "content": prompt}]
    return client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=system_prompt or DEFAULT_SYSTEM,
        messages=msgs,
    )
