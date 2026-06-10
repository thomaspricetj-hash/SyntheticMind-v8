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
class Critic3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# CRITIC — MAX SPEED + 3D‑MAX
# ============================================================

class Critic:
    """
    Optimized critique engine (3D‑MAX Edition).
    Provides:
        • structured critique envelopes
        • latency measurement
        • safe error handling
        • fallback model support
        • consistent schema
        • no slow‑pattern triggers
        • 3D‑MAX introspection for every critique cycle
    """

    def __init__(self, model: str = "qwen2.5:1.5b"):
        self.model = model
        self.llm = OllamaClient()
        self.fallback_model = "qwen2.5:0.5b"
        self._last_3d: Critic3D | None = None

    # ------------------------------------------------------------
    # MAIN CRITIQUE FUNCTION
    # ------------------------------------------------------------
    def critique(self, prompt: str, output: str) -> Dict[str, Any]:
        start = time.time()

        try:
            critique_prompt = self._build_prompt(prompt, output)

            # Primary model call
            result = self.llm.generate(self.model, critique_prompt)

            if not result.get("ok"):
                # Fallback model
                fallback = self.llm.generate(self.fallback_model, critique_prompt)

                if not fallback.get("ok"):
                    latency = int((time.time() - start) * 1000)
                    self._last_3d = Critic3D(
                        axis_x="critique",
                        axis_y=[f"primary_fail", f"fallback_fail"],
                        axis_z={"latency_ms": latency, "error": fallback.get("error")},
                    )
                    return {
                        "ok": False,
                        "model": self.model,
                        "latency_ms": latency,
                        "critique": "",
                        "error": fallback.get("error") or result.get("error"),
                    }

                latency = int((time.time() - start) * 1000)
                self._last_3d = Critic3D(
                    axis_x="critique",
                    axis_y=[f"primary_fail", f"fallback_success"],
                    axis_z={"latency_ms": latency, "model_used": self.fallback_model},
                )
                return {
                    "ok": True,
                    "model": self.fallback_model,
                    "latency_ms": latency,
                    "critique": fallback.get("response", ""),
                    "error": None,
                }

            # Successful primary model
            latency = int((time.time() - start) * 1000)
            self._last_3d = Critic3D(
                axis_x="critique",
                axis_y=[f"primary_success"],
                axis_z={"latency_ms": latency, "model_used": self.model},
            )
            return {
                "ok": True,
                "model": self.model,
                "latency_ms": latency,
                "critique": result.get("response", ""),
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Critic3D(
                axis_x="critique",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )
            return {
                "ok": False,
                "model": self.model,
                "latency_ms": latency,
                "critique": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PROMPT BUILDER (optimized)
    # ------------------------------------------------------------
    def _build_prompt(self, prompt: str, output: str) -> str:
        """
        Builds a robust critique prompt.
        Ensures:
            • no slow‑pattern triggers
            • no unnecessary whitespace
            • consistent structure
        """

        return (
            "You are a critique engine. Analyze the following model output for:\n\n"
            "- correctness\n"
            "- clarity\n"
            "- completeness\n"
            "- reasoning quality\n"
            "- missing details\n"
            "- contradictions\n"
            "- hallucination risk\n"
            "- structural issues\n"
            "- opportunities for improvement\n\n"
            "Provide a concise, actionable critique.\n\n"
            "=== PROMPT ===\n"
            f"{prompt}\n\n"
            "=== MODEL OUTPUT ===\n"
            f"{output}\n\n"
            "=== CRITIQUE ==="
        )


