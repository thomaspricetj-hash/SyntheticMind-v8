# syntheticmind/vision/vision_client.py

from __future__ import annotations
from typing import Dict, Any, Optional
import json
import base64
import time
import traceback
import urllib.request
import urllib.error


class VisionClient:
    """
    Local multimodal inference using Ollama (Qwen-VL, Llava, etc.)

    Features:
        • structured envelopes
        • latency measurement
        • safe HTTP execution
        • robust error handling
        • future-proof multimodal payloads
    """

    def __init__(self, model: str = "qwen2.5-vl"):
        self.model = model
        self.base = "http://127.0.0.1:11434"

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def analyze(self, prompt: str, image_bytes: bytes) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "model": str,
                "prompt": str,
                "response": str,
                "error": None
            }
        """

        start = time.time()

        try:
            encoded = base64.b64encode(image_bytes).decode("utf-8")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
            }

            data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw)

                response_text = parsed.get("response", "")

                return {
                    "ok": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "model": self.model,
                    "prompt": prompt,
                    "response": response_text,
                    "error": None,
                }

        except urllib.error.HTTPError as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": f"HTTPError {e.code}: {e.reason}",
                "traceback": traceback.format_exc(),
            }

        except urllib.error.URLError as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": f"URLError: {e.reason}",
                "traceback": traceback.format_exc(),
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

