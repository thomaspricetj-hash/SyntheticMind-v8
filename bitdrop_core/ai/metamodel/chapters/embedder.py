from __future__ import annotations
from typing import Any, Dict, List
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient

_OLLAMA_CLIENT = OllamaClient()


class Embedder:
    """
    Embedding generator using bge-large:latest.
    Clean version (no diagnostics).
    """

    def __init__(self, model_name: str = "bge-large:latest"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT

    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (packet.text or "").strip()

            if not text:
                return {
                    "ok": True,
                    "model": self.model_name,
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": [],
                    "notes": "empty input",
                    "escalate": False,
                }

            embedding: List[float] = self.ollama.embed(self.model_name, text)

            return {
                "ok": True,
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
                "output": embedding,
                "error": None,
                "escalate": False,
            }

        except Exception as e:
            return {
                "ok": False,
                "model": self.model_name,
                "latency_ms": int((time.time() - start) * 1000),
                "output": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
                "escalate": False,
            }
