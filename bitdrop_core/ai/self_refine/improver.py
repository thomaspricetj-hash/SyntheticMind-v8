from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import time
import traceback

from ..metamodel.ollama_client import OllamaClient


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Improver3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# IMPROVER — MAX SPEED + 3D‑MAX
# ============================================================

class Improver:
    """
    Optimized improvement engine (3D‑MAX Edition).
    Provides:
        • structured envelopes
        • latency measurement
        • critique‑aware prompt shaping
        • safe error handling
        • fallback model support
        • no slow‑pattern triggers
        • 3D‑MAX introspection for every improvement cycle
    """

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.llm = OllamaClient()
        self.fallback_model = "qwen2.5:3b"
        self._last_3d: Improver3D | None = None

    # ------------------------------------------------------------
    # MAIN IMPROVEMENT FUNCTION
    # ------------------------------------------------------------
    def improve(self, prompt: str, output: str, critique: str) -> Dict[str, Any]:
        start = time.time()

        try:
            improve_prompt = self._build_prompt(prompt, output, critique)

            # Primary model call
            result = self.llm.generate(self.model, improve_prompt)

            if not result.get("ok"):
                # Fallback model
                fallback = self.llm.generate(self.fallback_model, improve_prompt)

                if not fallback.get("ok"):
                    latency = int((time.time() - start) * 1000)
                    self._last_3d = Improver3D(
                        axis_x="improve",
                        axis_y=["primary_fail", "fallback_fail"],
                        axis_z={"latency_ms": latency, "error": fallback.get("error")},
                    )
                    return {
                        "ok": False,
                        "model": self.model,
                        "latency_ms": latency,
                        "improved": "",
                        "error": fallback.get("error") or result.get("error"),
                    }

                latency = int((time.time() - start) * 1000)
                self._last_3d = Improver3D(
                    axis_x="improve",
                    axis_y=["primary_fail", "fallback_success"],
                    axis_z={"latency_ms": latency, "model_used": self.fallback_model},
                )
                return {
                    "ok": True,
                    "model": self.fallback_model,
                    "latency_ms": latency,
                    "improved": fallback.get("response", ""),
                    "error": None,
                }

            # Successful primary model
            latency = int((time.time() - start) * 1000)
            self._last_3d = Improver3D(
                axis_x="improve",
                axis_y=["primary_success"],
                axis_z={"latency_ms": latency, "model_used": self.model},
            )
            return {
                "ok": True,
                "model": self.model,
                "latency_ms": latency,
                "improved": result.get("response", ""),
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Improver3D(
                axis_x="improve",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )
            return {
                "ok": False,
                "model": self.model,
                "latency_ms": latency,
                "improved": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PROMPT BUILDER (optimized)
    # ------------------------------------------------------------
    def _build_prompt(self, prompt: str, output: str, critique: str) -> str:
        return (
            "You are an improvement engine.\n\n"
            "Your task:\n"
            "- Fix all issues identified in the critique.\n"
            "- Improve clarity, correctness, completeness, and reasoning quality.\n"
            "- Preserve the original intent of the output.\n"
            "- Do NOT mention the critique or the improvement process.\n\n"
            "=== ORIGINAL PROMPT ===\n"
            f"{prompt}\n\n"
            "=== ORIGINAL OUTPUT ===\n"
            f"{output}\n\n"
            "=== CRITIQUE ===\n"
            f"{critique}\n\n"
            "=== IMPROVED OUTPUT ==="
        )


