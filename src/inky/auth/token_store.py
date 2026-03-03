"""Persistent token storage with secure file permissions."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


CONFIG_DIR = Path.home() / ".config" / "inky"
TOKEN_FILE = CONFIG_DIR / "tokens.json"


class TokenStore:
    """Manages OAuth token persistence."""

    def __init__(self, path: Path = TOKEN_FILE) -> None:
        self.path = path

    def save(self, tokens: dict) -> None:
        """Save tokens to disk with restricted permissions."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Store the time we received the tokens so we can check expiry
        tokens["stored_at"] = time.time()

        self.path.write_text(json.dumps(tokens, indent=2))
        os.chmod(self.path, 0o600)

    def load(self) -> dict | None:
        """Load tokens from disk, or None if not present."""
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def clear(self) -> None:
        """Remove stored tokens."""
        if self.path.exists():
            self.path.unlink()

    def is_expired(self, tokens: dict) -> bool:
        """Check if the access token is expired or within 1 hour of expiry."""
        stored_at = tokens.get("stored_at", 0)
        expires_in = tokens.get("expires_in", 0)
        if not stored_at or not expires_in:
            return True
        # Refresh 1 hour before actual expiry
        expiry_time = stored_at + expires_in - 3600
        return time.time() >= expiry_time
