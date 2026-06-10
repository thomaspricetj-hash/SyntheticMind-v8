# syntheticmind/vision/vision_client.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import json
import base64
import time
import traceback
import urllib.request
import urllib.error


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Vision3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# VISION CLIENT — MAX MULTIMODAL + 3D‑MAX
# ============================================================

class VisionClient:
    """
    Local multimodal inference using Ollama (Qwen-VL, Llava, etc.) (3D‑MAX Edition)

    Features:
        • structured envelopes
        • latency measurement
        • safe HTTP execution
        • robust error handling
        • future-proof multimodal payloads
        • 3D‑MAX telemetry
    """

    def __init__(self, model: str = "qwen2.5-vl"):
        self.model = model
        self.base = "http://127.0.0.1:11434"
        self._last_3d: Optional[Vision3D] = None

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

                latency = int((time.time() - start) * 1000)

                self._last_3d = Vision3D(
                    axis_x="analyze",
                    axis_y=[f"prompt_len:{len(prompt)}"],
                    axis_z={
                        "latency_ms": latency,
                        "response_len": len(response_text),
                        "ok": True,
                    },
                )

                return {
                    "ok": True,
                    "latency_ms": latency,
                    "model": self.model,
                    "prompt": prompt,
                    "response": response_text,
                    "error": None,
                }

        except urllib.error.HTTPError as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = Vision3D(
                axis_x="analyze",
                axis_y=["http_error"],
                axis_z={"latency_ms": latency, "code": e.code},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": f"HTTPError {e.code}: {e.reason}",
                "traceback": traceback.format_exc(),
            }

        except urllib.error.URLError as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = Vision3D(
                axis_x="analyze",
                axis_y=["url_error"],
                axis_z={"latency_ms": latency, "reason": str(e.reason)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": f"URLError: {e.reason}",
                "traceback": traceback.format_exc(),
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = Vision3D(
                axis_x="analyze",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "model": self.model,
                "prompt": prompt,
                "response": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


