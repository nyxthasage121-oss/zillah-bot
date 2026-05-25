"""Shared Anthropic client, initialized once at startup via clients.init()."""
import anthropic

client: anthropic.Anthropic | None = None


def init(api_key: str) -> None:
    global client
    client = anthropic.Anthropic(api_key=api_key)
