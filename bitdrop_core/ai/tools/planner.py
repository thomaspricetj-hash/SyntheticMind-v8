# syntheticmind/tools/planner.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import traceback

from ..metamodel.ollama_client import OllamaClient


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Planner3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# PLANNER — MAX COMMAND + 3D‑MAX
# ============================================================

class Planner:
    """
    Converts natural language into tool commands (3D‑MAX Edition).

    Produces:
        • structured envelopes
        • validated tool commands
        • deterministic formatting
        • safe fallback behavior
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.llm = OllamaClient()
        self.model = "qwen2.5:1.5b"
        self._last_3d: Optional[Planner3D] = None

    # ------------------------------------------------------------
    # INTERNAL: NORMALIZE COMMAND
    # ------------------------------------------------------------
    def _normalize(self, raw: str) -> str:
        """
        Clean up whitespace, strip quotes, ensure deterministic formatting.
        """

        if not isinstance(raw, str):
            self._last_3d = Planner3D(
                axis_x="_normalize",
                axis_y=["non_string"],
                axis_z={"ok": False},
            )
            return ""

        cleaned = raw.strip()

        # Remove accidental quoting
        if cleaned.startswith(("'", '"')) and cleaned.endswith(("'", '"')):
            cleaned = cleaned[1:-1].strip()

        self._last_3d = Planner3D(
            axis_x="_normalize",
            axis_y=[f"len:{len(cleaned)}"],
            axis_z={"ok": True},
        )

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

            latency = int((time.time() - start) * 1000)

            self._last_3d = Planner3D(
                axis_x="plan",
                axis_y=[f"instr_len:{len(instruction)}"],
                axis_z={
                    "latency_ms": latency,
                    "command_len": len(command),
                    "ok": True,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "instruction": instruction,
                "command": command,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = Planner3D(
                axis_x="plan",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "instruction": instruction,
                "command": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

