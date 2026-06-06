# ai/llm/ollama_client.py

import json
import urllib.request
import urllib.error
import socket
from typing import Dict, Any, Optional


class OllamaClient:
    """
    Robust Ollama HTTP client for local model inference.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 11434, timeout: int = 60):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout

    def generate(
        self,
        model: str,
        prompt: str,
        timeout: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if options:
            payload["options"] = options

        data = json.dumps(payload).encode("utf-8")

        # ⭐ FIXED: correct endpoint
        req = urllib.request.Request(
            f"{self.base}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        timeout = timeout or self.timeout

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")

                if resp.status != 200:
                    return {
                        "ok": False,
                        "model": model,
                        "response": "",
                        "error": f"HTTP {resp.status}: {raw}",
                    }

                try:
                    result = json.loads(raw)
                except json.JSONDecodeError:
                    return {
                        "ok": False,
                        "model": model,
                        "response": "",
                        "error": f"Malformed JSON from Ollama: {raw}",
                    }

                return {
                    "ok": True,
                    "model": model,
                    "response": result.get("response", ""),
                    "error": None,
                }

        except urllib.error.HTTPError as e:
            return {
                "ok": False,
                "model": model,
                "response": "",
                "error": f"HTTPError {e.code}: {e.reason}",
            }

        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                return {
                    "ok": False,
                    "model": model,
                    "response": "",
                    "error": "Connection refused — is Ollama running?",
                }

            if isinstance(e.reason, socket.timeout):
                return {
                    "ok": False,
                    "model": model,
                    "response": "",
                    "error": "Request timed out",
                }

            return {
                "ok": False,
                "model": model,
                "response": "",
                "error": f"URLError: {e.reason}",
            }

        except Exception as e:
            return {
                "ok": False,
                "model": model,
                "response": "",
                "error": f"Unexpected error: {e}",
            }


