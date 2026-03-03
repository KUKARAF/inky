"""Authentication for the Anthropic API.

Currently supports API key authentication via:
  1. ANTHROPIC_API_KEY environment variable
  2. Key stored in ~/.config/inky/api_key

OAuth 2.0 + PKCE support is stubbed out for when Anthropic opens
third-party OAuth app registration.
"""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "inky"
API_KEY_FILE = CONFIG_DIR / "api_key"


def _read_stored_key() -> str | None:
    """Read API key from config file."""
    if API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text().strip()
        if key:
            return key
    return None


def save_api_key(key: str) -> None:
    """Store an API key to disk with restricted permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    API_KEY_FILE.write_text(key)
    os.chmod(API_KEY_FILE, 0o600)


def get_access_token() -> str:
    """Get a valid API key for Anthropic.

    Checks in order:
    1. ANTHROPIC_API_KEY environment variable
    2. Stored key in ~/.config/inky/api_key

    Raises RuntimeError if no key is found.
    """
    # Check env var first
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    # Check stored key file
    stored = _read_stored_key()
    if stored:
        return stored

    raise RuntimeError(
        "No Anthropic API key found.\n\n"
        "Set your API key using one of these methods:\n"
        "  1. Environment variable: export ANTHROPIC_API_KEY=sk-ant-...\n"
        "  2. Config file: echo 'sk-ant-...' > ~/.config/inky/api_key\n\n"
        "Get your API key at: https://console.anthropic.com/settings/keys"
    )


def authenticate() -> str:
    """Prompt-based authentication — returns the API key or raises."""
    return get_access_token()
