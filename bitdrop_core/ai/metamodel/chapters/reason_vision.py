from __future__ import annotations
from typing import Any, Dict
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient

_OLLAMA_CLIENT = OllamaClient()


class ReasonVision:
    """
    Vision reasoning using qwen3-vl:8b.
    Expects image bytes in packet.data.
    Clean, diagnostics‑free, production‑ready.
    """

    def __init__(self, model_name: str = "qwen3-vl:8b"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT

    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (packet.text or "").strip()
            image_bytes = getattr(packet, "data", None)

            # No image → structured error
            if image_bytes is None:
                return {
                    "ok": False,
                    "model": self.model_name,
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": "",
                    "error": "no image data provided",
                    "escalate": False,
                }

            # ----------------------------------------------------
            # CALL OLLAMA (VISION‑ENABLED MODEL)
            # ----------------------------------------------------
            # Your OllamaClient supports passing images via keyword
            result = self.ollama.generate(
                self.model_name,
                text,
                options={"image": image_bytes}
            )

            # Hard failure from Ollama
            if not result.get("ok"):
                return {
                    "ok": False,
                    "model": self.model_name,
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": "",
                    "error": result.get("error"),
                    "escalate": False,
                }

            # Extract clean text
            output = result.get("response", "")
            if not isinstance(output, str):
                output = str(output)

            return {
                "ok": True,
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
                "output": output.strip(),
                "error": None,
                "escalate": False,
            }

        except Exception as e:
            # Fully structured fallback
            return {
                "ok": False,
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
                "output": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "escalate": False,
            }
