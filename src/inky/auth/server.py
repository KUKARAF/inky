"""Local HTTP callback server for OAuth redirect."""

from __future__ import annotations

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the OAuth redirect callback."""

    result: dict
    expected_state: str

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/oauth/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = parse_qs(parsed.query)
        state = params.get("state", [None])[0]

        if state != self.expected_state:
            self.result["error"] = "State mismatch — possible CSRF attack"
            self._respond("Authentication failed: state mismatch. You can close this tab.")
            return

        error = params.get("error", [None])[0]
        if error:
            self.result["error"] = error
            self._respond(f"Authentication failed: {error}. You can close this tab.")
            return

        code = params.get("code", [None])[0]
        if not code:
            self.result["error"] = "No authorization code received"
            self._respond("Authentication failed: no code. You can close this tab.")
            return

        self.result["code"] = code
        self._respond(
            "Authentication successful! You can close this tab and return to Inkscape."
        )

        # Shut down the server after handling
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _respond(self, message: str) -> None:
        body = f"""<!DOCTYPE html>
<html><head><title>inky</title>
<style>
body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center;
       align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }}
.card {{ background: white; padding: 2rem; border-radius: 12px;
         box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; max-width: 400px; }}
</style></head>
<body><div class="card"><p>{message}</p></div></body></html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, format: str, *args: object) -> None:
        # Suppress default request logging
        pass


def run_callback_server(expected_state: str, result: dict) -> int:
    """Start a local HTTP server for the OAuth callback.

    The server binds to 127.0.0.1 on an ephemeral port and runs in a
    background thread. It populates `result` with either {"code": "..."}
    or {"error": "..."} when the callback is received.

    Args:
        expected_state: The OAuth state parameter to validate.
        result: Mutable dict that will be populated with the callback result.

    Returns:
        The port number the server is listening on.
    """
    handler = type(
        "_Handler",
        (_CallbackHandler,),
        {"result": result, "expected_state": expected_state},
    )
    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return port
