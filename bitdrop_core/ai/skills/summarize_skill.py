# ai/skills/summarize_skill.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Summarize3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SUMMARIZE SKILL — MAX SPEED + 3D‑MAX
# ============================================================

class SummarizeSkill:
    """
    High‑performance summarization skill using the runtime's small reasoning model.
    3D‑MAX Edition.

    Features:
        • structured envelopes
        • latency measurement
        • mutation-aware (EvolutionEngine)
        • prompt_prefix support
        • evaluator‑friendly summarization
        • safe fallback logic
        • 3D‑MAX introspection for every run
    """

    # ------------------------------------------------------------
    # REQUIRED METADATA FOR SkillRegistry + EvolutionEngine
    # ------------------------------------------------------------
    name = "summarize"
    description = "Summarize text into a concise, clear explanation."
    version = "1.0.0"
    author = "system"
    family = "nlp"
    mutable = True

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self._last_3d: Optional[Summarize3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        params:
            {
                "text": str,
                "prompt_prefix": str (optional, used by mutated variants)
            }
        """

        start = time.time()

        try:
            text = params.get("text", "")
            prefix = params.get("prompt_prefix", "")

            if not isinstance(text, str) or not text.strip():
                raise ValueError("missing or invalid 'text' parameter")

            # ----------------------------------------------------
            # BUILD PROMPT (deterministic, evaluator‑friendly)
            # ----------------------------------------------------
            prompt = (
                f"{prefix}"
                "Summarize the following text in a concise, clear, evaluator‑friendly way. "
                "Preserve key facts, avoid filler, avoid meta‑commentary.\n\n"
                f"TEXT:\n{text}\n\n"
                "SUMMARY:"
            )

            # ----------------------------------------------------
            # CALL RUNTIME (small reasoning model)
            # ----------------------------------------------------
            result = self.runtime.generate(
                text=prompt,
                intent="small_reasoning"
            )

            # Extract output from structured envelope
            output = result.get("output", result)

            latency_ms = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = Summarize3D(
                axis_x="run",
                axis_y=[f"input_len:{len(text)}", f"mutation:{bool(prefix)}"],
                axis_z={
                    "latency_ms": latency_ms,
                    "ok": True,
                    "model_used": result.get("model"),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency_ms,
                "input_length": len(text),
                "summary": output,
                "mutation_used": bool(prefix),
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)

            self._last_3d = Summarize3D(
                axis_x="run",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": latency_ms,
                    "ok": False,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "latency_ms": latency_ms,
                "input_length": len(params.get("text", "")),
                "summary": None,
                "mutation_used": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }



