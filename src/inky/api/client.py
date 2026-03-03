"""Anthropic Messages API client."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Generator

import httpx

from inky.auth import get_access_token

API_BASE = "https://api.anthropic.com"
MESSAGES_URL = f"{API_BASE}/v1/messages"
API_VERSION = "2023-06-01"

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 4096


class ClaudeClient:
    """Client for the Anthropic Messages API."""

    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self.model = model
        self._token: str | None = None

    def _get_headers(self) -> dict[str, str]:
        """Build request headers with auth."""
        token = self._ensure_token()

        headers = {
            "Content-Type": "application/json",
            "anthropic-version": API_VERSION,
            "anthropic-client-platform": "inky",
        }

        # Distinguish between API key and OAuth Bearer token
        if token.startswith("sk-ant-"):
            headers["x-api-key"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _ensure_token(self) -> str:
        """Get or refresh the access token."""
        if self._token is None:
            self._token = get_access_token()
        return self._token

    def _invalidate_token(self) -> None:
        """Clear cached token so it gets refreshed on next call."""
        self._token = None

    def message(
        self,
        user_message: str,
        system: str | None = None,
        conversation: list[dict] | None = None,
        max_tokens: int = MAX_TOKENS,
    ) -> str:
        """Send a message and return the assistant's text response.

        Args:
            user_message: The user's message text.
            system: Optional system prompt.
            conversation: Optional prior conversation messages.
                          Each dict should have "role" and "content" keys.
            max_tokens: Maximum response tokens.

        Returns:
            The assistant's response text.
        """
        messages = list(conversation) if conversation else []
        messages.append({"role": "user", "content": user_message})

        body: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system

        response = self._request(body)
        # Extract text from content blocks
        content = response.get("content", [])
        text_parts = [
            block["text"] for block in content if block.get("type") == "text"
        ]
        return "\n".join(text_parts)

    def message_stream(
        self,
        user_message: str,
        system: str | None = None,
        conversation: list[dict] | None = None,
        max_tokens: int = MAX_TOKENS,
    ) -> Generator[str, None, None]:
        """Send a message and yield response text chunks via SSE streaming.

        Args:
            user_message: The user's message text.
            system: Optional system prompt.
            conversation: Optional prior conversation messages.
            max_tokens: Maximum response tokens.

        Yields:
            Text chunks as they arrive.
        """
        messages = list(conversation) if conversation else []
        messages.append({"role": "user", "content": user_message})

        body: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "stream": True,
        }
        if system:
            body["system"] = system

        yield from self._request_stream(body)

    def _request(self, body: dict, retry: int = 1) -> dict:
        """Make a non-streaming API request with retry on 401/429."""
        headers = self._get_headers()
        with httpx.Client(timeout=120) as client:
            resp = client.post(MESSAGES_URL, headers=headers, json=body)

            if resp.status_code == 401 and retry > 0:
                self._invalidate_token()
                return self._request(body, retry=retry - 1)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", "5"))
                time.sleep(retry_after)
                return self._request(body, retry=retry)

            resp.raise_for_status()
            return resp.json()

    def _request_stream(self, body: dict) -> Generator[str, None, None]:
        """Make a streaming API request, yielding text deltas."""
        headers = self._get_headers()
        with httpx.Client(timeout=120) as client:
            with client.stream(
                "POST", MESSAGES_URL, headers=headers, json=body
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield delta.get("text", "")
