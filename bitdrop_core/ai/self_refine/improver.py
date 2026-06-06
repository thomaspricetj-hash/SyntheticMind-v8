# syntheticmind/metamodel/improver.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from ..metamodel.ollama_client import OllamaClient


class Improver:
    """
    Improves the model's output based on critique.
    Provides:
        • structured improvement envelopes
        • latency measurement
        • safe error handling
        • critique‑aware prompt building
        • future‑proof refinement engine
    """

    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.llm = OllamaClient()

    # ------------------------------------------------------------
    # MAIN IMPROVEMENT FUNCTION
    # ------------------------------------------------------------
    def improve(self, prompt: str, output: str, critique: str) -> Dict[str, Any]:
        """
        Returns a structured improvement envelope:
            {
                "ok": bool,
                "model": str,
                "latency_ms": int,
                "improved": str,
                "error": str | None
            }
        """

        start = time.time()

        try:
            improve_prompt = self._build_prompt(prompt, output, critique)

            # Call Ollama
            result = self.llm.generate(self.model, improve_prompt)

            # result is a structured envelope from the upgraded OllamaClient:
            # {
            #   "ok": bool,
            #   "model": str,
            #   "response": str,
            #   "error": str | None
            # }

            if not result.get("ok"):
                return {
                    "ok": False,
                    "model": self.model,
                    "latency_ms": int((time.time() - start) * 1000),
                    "improved": "",
                    "error": result.get("error"),
                }

            return {
                "ok": True,
                "model": self.model,
                "latency_ms": int((time.time() - start) * 1000),
                "improved": result.get("response", ""),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "model": self.model,
                "latency_ms": int((time.time() - start) * 1000),
                "improved": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PROMPT BUILDER
    # ------------------------------------------------------------
    def _build_prompt(self, prompt: str, output: str, critique: str) -> str:
        """
        Builds a robust improvement prompt.
        """

        return f"""
You are an improvement engine.

Your task:
- Fix all issues identified in the critique.
- Improve clarity, correctness, completeness, and reasoning quality.
- Preserve the original intent of the output.
- Do NOT mention the critique or the improvement process.

=== ORIGINAL PROMPT ===
{prompt}

=== ORIGINAL OUTPUT ===
{output}

=== CRITIQUE ===
{critique}

=== IMPROVED OUTPUT ===
""".strip()

