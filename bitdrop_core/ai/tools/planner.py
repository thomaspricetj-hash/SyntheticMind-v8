# syntheticmind/tools/planner.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from ..metamodel.ollama_client import OllamaClient


class Planner:
    """
    Converts natural language into tool commands.

    Produces:
        • structured envelopes
        • validated tool commands
        • deterministic formatting
        • safe fallback behavior
    """

    def __init__(self):
        self.llm = OllamaClient()
        self.model = "qwen2.5:1.5b"

    # ------------------------------------------------------------
    # INTERNAL: NORMALIZE COMMAND
    # ------------------------------------------------------------
    def _normalize(self, raw: str) -> str:
        """
        Clean up whitespace, strip quotes, ensure deterministic formatting.
        """

        if not isinstance(raw, str):
            return ""

        cleaned = raw.strip()

        # Remove accidental quoting
        if cleaned.startswith(("'", '"')) and cleaned.endswith(("'", '"')):
            cleaned = cleaned[1:-1].strip()

        return cleaned

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def plan(self, instruction: str) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "instruction": str,
                "command": str,
                "error": None
            }
        """

        start = time.time()

        try:
            prompt = (
                "You are a tool planner. Convert the user's instruction into a tool command.\n\n"
                "Tools:\n"
                "- python: <code>\n"
                "- read: <path>\n"
                "- write: <path>|<content>\n\n"
                "User instruction:\n"
                f"{instruction}\n\n"
                "Return ONLY the tool command."
            )

            raw = self.llm.generate(self.model, prompt)
            command = self._normalize(raw)

            if not command:
                raise ValueError("LLM returned empty command")

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "instruction": instruction,
                "command": command,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "instruction": instruction,
                "command": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

