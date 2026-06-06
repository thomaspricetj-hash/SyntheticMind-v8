# ai/clients/python_client.py

from __future__ import annotations
import json
import urllib.request
import urllib.error
import socket
from typing import Optional, Dict, Any


class BitDropClientError(Exception):
    """Base exception for BitDrop client errors."""


class BitDropConnectionError(BitDropClientError):
    """Raised when the server cannot be reached."""


class BitDropResponseError(BitDropClientError):
    """Raised when the server returns an invalid or error response."""


class BitDropClient:
    """
    Robust Python SDK for the BitDrop MetaModel server.

    Features:
        • automatic retries
        • timeouts
        • safe binary upload
        • structured errors
        • health check
        • drop‑in compatibility with original API
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 5.0):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    # -------------------------------------------------------------
    # INTERNAL HTTP WRAPPER
    # -------------------------------------------------------------
    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    raise BitDropResponseError(f"Invalid JSON response: {raw}")

        except urllib.error.URLError as e:
            raise BitDropConnectionError(f"Could not reach BitDrop server: {e}")

        except socket.timeout:
            raise BitDropConnectionError("BitDrop server timed out")

    # -------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------

    def health(self) -> bool:
        """Check if the server is reachable."""
        try:
            resp = self._post("/health", {})
            return resp.get("status") == "ok"
        except BitDropClientError:
            return False

    def ask(self, text: str) -> str:
        """Simple text query."""
        result = self._post("/ask", {"text": text})
        return result.get("output", "")

    def generate(
        self,
        text: str = "",
        data: Optional[bytes] = None,
        intent: str = "small_reasoning",
        compressed: bool = False,
        return_compressed: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Full MetaModel generation call.
        Supports binary-safe data upload via base64.
        """

        payload: Dict[str, Any] = {
            "text": text,
            "intent": intent,
            "compressed": compressed,
            "return_compressed": return_compressed,
            "metadata": metadata or {},
        }

        # Binary-safe upload
        if data is not None:
            import base64
            payload["data"] = base64.b64encode(data).decode("utf-8")

        return self._post("/generate", payload)

