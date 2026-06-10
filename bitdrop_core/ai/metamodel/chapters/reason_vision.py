from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import traceback

from ..context.packet import Packet
from ..ollama_client import OllamaClient

_OLLAMA_CLIENT = OllamaClient()


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ReasonVision3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# REASON VISION — MAX MULTIMODAL REASONING + 3D‑MAX
# ============================================================

class ReasonVision:
    """
    Vision reasoning using qwen3-vl:8b (3D‑MAX Edition).
    Expects image bytes in packet.data.
    Clean, deterministic, production‑ready, telemetry‑enhanced.
    """

    def __init__(self, model_name: str = "qwen3-vl:8b"):
        self.model_name = model_name
        self.ollama = _OLLAMA_CLIENT
        self._last_3d: Optional[ReasonVision3D] = None

    # ------------------------------------------------------------
    # MAIN EXECUTION
    # ------------------------------------------------------------
    def run(self, packet: Packet) -> Dict[str, Any]:
        start = time.time()

        try:
            text = (packet.text or "").strip()
            image_bytes = getattr(packet, "data", None)

            # ----------------------------------------------------
            # NO IMAGE PROVIDED
            # ----------------------------------------------------
            if image_bytes is None:
                latency = int((time.time() - start) * 1000)

                self._last_3d = ReasonVision3D(
                    axis_x="run",
                    axis_y=["missing_image"],
                    axis_z={"latency_ms": latency},
                )

                return {
                    "ok": False,
                    "model": self.model_name,
                    "latency_ms": latency,
                    "output": "",
                    "error": "no image data provided",
                    "escalate": False,
                }

            # ----------------------------------------------------
            # MODEL CALL (VISION‑ENABLED)
            # ----------------------------------------------------
            result = self.ollama.generate(
                self.model_name,
                text,
                options={"image": image_bytes},
            )

            # Hard failure from Ollama
            if not result.get("ok"):
                latency = int((time.time() - start) * 1000)

                self._last_3d = ReasonVision3D(
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
            self._last_3d = ReasonVision3D(
                axis_x="run",
                axis_y=[
                    f"text_len:{len(text)}",
                    f"image_bytes:{len(image_bytes) if image_bytes else 0}",
                ],
                axis_z={
                    "latency_ms": latency,
                    "output_len": len(output),
                    "ok": True,
                },
            )

            # ----------------------------------------------------
            # SUCCESSFUL MULTIMODAL OUTPUT
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
            self._last_3d = ReasonVision3D(
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

