# syntheticmind/metamodel/critic.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from ..metamodel.ollama_client import OllamaClient


class Critic:
    """
    Evaluates the model's output and identifies issues.
    Provides:
        • structured critique envelopes
        • latency measurement
        • safe error handling
        • future-proof critique prompt
        • consistent with ReasonSmall/ReasonLarge
    """

    def __init__(self, model: str = "qwen2.5:1.5b"):
        self.model = model
        self.llm = OllamaClient()

    # ------------------------------------------------------------
    # MAIN CRITIQUE FUNCTION
    # ------------------------------------------------------------
    def critique(self, prompt: str, output: str) -> Dict[str, Any]:
        """
        Returns a structured critique envelope:
            {
                "ok": bool,
                "model": str,
                "latency_ms": int,
                "critique": str,
                "error": str | None
            }
        """

        start = time.time()

        try:
            critique_prompt = self._build_prompt(prompt, output)

            # Call Ollama
            result = self.llm.generate(self.model, critique_prompt)

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
                    "critique": "",
                    "error": result.get("error"),
                }

            return {
                "ok": True,
                "model": self.model,
                "latency_ms": int((time.time() - start) * 1000),
                "critique": result.get("response", ""),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "model": self.model,
                "latency_ms": int((time.time() - start) * 1000),
                "critique": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PROMPT BUILDER
    # ------------------------------------------------------------
    def _build_prompt(self, prompt: str, output: str) -> str:
        """
        Builds a robust critique prompt.
        """

        return f"""
You are a critique engine. Analyze the following model output for:

- correctness
- clarity
- completeness
- reasoning quality
- missing details
- contradictions
- hallucination risk
- structural issues
- opportunities for improvement

Provide a concise, actionable critique.

=== PROMPT ===
{prompt}

=== MODEL OUTPUT ===
{output}

=== CRITIQUE ===
""".strip()

