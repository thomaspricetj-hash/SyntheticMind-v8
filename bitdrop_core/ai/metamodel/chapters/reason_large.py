from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient


# ------------------------------------------------------------
# GLOBAL SINGLETON CLIENT (FAST)
# ------------------------------------------------------------
_OLLAMA_CLIENT = OllamaClient()


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ReasonLarge3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# REASON LARGE — MAX DEEP REASONING + 3D‑MAX
# ============================================================

class ReasonLarge:
    """
    Deep reasoning using a large local Ollama model (3D‑MAX Edition).
    Clean, deterministic, production‑ready, telemetry‑enhanced.
    """

    def __init__(self, model_name: str = "qwen2.5:7b"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT   # singleton for speed
        self._last_3d: Optional[ReasonLarge3D] = None

    # ------------------------------------------------------------
    # MAIN EXECUTION
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

                self._last_3d = ReasonLarge3D(
                    axis_x="run",
                    axis_y=["empty_input"],
                    axis_z={"latency_ms": latency},
                )

                return {
                    "ok": True,
                    "model": self.model_name,
                    "latency_ms": latency,
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
                latency = int((time.time() - start) * 1000)

                self._last_3d = ReasonLarge3D(
                    axis_x="run",
                    axis_y=["ollama_error"],
                    axis_z={"latency_ms": latency, "error": result.get("error")},
                )

                return {
                    "ok": False,
                    "model": self.model_name,
                    "latency_ms": latency,
                    "output": "",
                    "error": result.get("error"),
                    "escalate": False,
                }

            # Extract clean text
            output = result.get("response", "")
            if not isinstance(output, str):
                output = str(output)

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = ReasonLarge3D(
                axis_x="run",
                axis_y=[f"text_len:{len(text)}"],
                axis_z={
                    "latency_ms": latency,
                    "output_len": len(output),
                    "ok": True,
                },
            )

            # ----------------------------------------------------
            # SUCCESSFUL LARGE-MODEL OUTPUT
            # ----------------------------------------------------
            return {
                "ok": True,
                "model": self.model_name,
                "latency_ms": latency,
                "output": output.strip(),
                "error": None,
                "escalate": False,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = ReasonLarge3D(
                axis_x="run",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            # Fully structured fallback
            return {
                "ok": False,
                "model": self.model_name,
                "latency_ms": latency,
                "output": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
                "escalate": False,
            }





