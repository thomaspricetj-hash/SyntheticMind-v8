# ai/skills/summarize_skill.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback


class SummarizeSkill:
    """
    High-performance summarization skill using the runtime's small reasoning model.

    Features:
        • structured envelopes
        • latency measurement
        • mutation-aware (EvolutionEngine)
        • prompt_prefix support
        • evaluator-friendly summarization
        • safe fallback logic
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
            # BUILD PROMPT
            # ----------------------------------------------------
            prompt = (
                f"{prefix}"
                "Summarize the following text in a concise, clear, evaluator-friendly way. "
                "Preserve key facts, avoid filler, avoid meta-commentary.\n\n"
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

            # Runtime returns structured envelope; extract output
            output = result.get("output", result)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "input_length": len(text),
                "summary": output,
                "mutation_used": bool(prefix),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "input_length": len(params.get("text", "")),
                "summary": None,
                "mutation_used": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


