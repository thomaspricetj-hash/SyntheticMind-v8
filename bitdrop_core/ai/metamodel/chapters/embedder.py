from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient

_OLLAMA_CLIENT = OllamaClient()


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Embed3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# EMBEDDER — MAX EMBEDDING + 3D‑MAX
# ============================================================

class Embedder:
    """
    Embedding generator using bge-large:latest (3D‑MAX Edition).
    Clean, deterministic, telemetry‑enhanced.
    """

    def __init__(self, model_name: str = "bge-large:latest"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT
        self._last_3d: Optional[Embed3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (packet.text or "").strip()

            # ----------------------------------------------------
            # EMPTY INPUT
            # ----------------------------------------------------
            if not text:
                latency = int((time.time() - start) * 1000)

                self._last_3d = Embed3D(
                    axis_x="run",
                    axis_y=["empty_input"],
                    axis_z={"latency_ms": latency},
                )

                return {
                    "ok": True,
                    "model": self.model_name,
                    "latency_ms": latency,
                    "output": [],
                    "notes": "empty input",
                    "escalate": False,
                }

            # ----------------------------------------------------
            # REAL EMBEDDING
            # ----------------------------------------------------
            embedding: List[float] = self.ollama.embed(self.model_name, text)

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = Embed3D(
                axis_x="run",
                axis_y=[f"text_len:{len(text)}"],
                axis_z={
                    "latency_ms": latency,
                    "dim": len(embedding),
                    "ok": True,
                },
            )

            return {
                "ok": True,
                "model": self.model_name,
                "latency_ms": latency,
                "output": embedding,
                "error": None,
                "escalate": False,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = Embed3D(
                axis_x="run",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "model": self.model_name,
                "latency_ms": latency,
                "output": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
                "escalate": False,
            }
