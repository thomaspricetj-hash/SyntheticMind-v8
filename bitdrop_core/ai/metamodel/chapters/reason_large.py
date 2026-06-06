# syntheticmind/chapters/reason_large.py

from __future__ import annotations
from typing import Any, Dict
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient


# ------------------------------------------------------------
# GLOBAL SINGLETON CLIENT (FAST)
# ------------------------------------------------------------
_OLLAMA_CLIENT = OllamaClient()


class ReasonLarge:
    """
    Deep reasoning using a large local Ollama model.
    Clean, diagnostics‑free, production‑ready.
    """

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT   # singleton for speed

    # ------------------------------------------------------------
    # MAIN EXECUTION
    # ------------------------------------------------------------
    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (packet.text or "").strip()

            # Empty input → structured no‑op
            if not text:
                return {
                    "ok": True,
                    "model": self.model_name,
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": "",
                    "notes": "empty input",
                    "escalate": False,
                }

            # ----------------------------------------------------
            # CALL OLLAMA (FAST, CACHED CLIENT)
            # ----------------------------------------------------
            result = self.ollama.generate(self.model_name, text)

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

            # ----------------------------------------------------
            # SUCCESSFUL LARGE-MODEL OUTPUT
            # ----------------------------------------------------
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




