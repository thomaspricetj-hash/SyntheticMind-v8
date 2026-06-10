from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Skill3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SKILL — MAX SPEED + 3D‑MAX
# ============================================================

class Skill:
    """
    Base class for reusable skills — 3D‑MAX EDITION.
    A skill is a named, parameterized workflow.

    Provides:
        • structured envelopes
        • latency measurement
        • safe execution wrapper
        • parameter validation hook
        • evolution metadata
        • 3D‑MAX introspection
        • future‑proof interface for SkillRegistry + SkillRunner
    """

    # ------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------
    name: str = "base-skill"
    description: str = "Base skill"
    version: str = "1.0.0"

    def __init__(self):
        self._last_3d: Skill3D | None = None

    # ------------------------------------------------------------
    # PUBLIC ENTRYPOINT
    # ------------------------------------------------------------
    def __call__(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safe wrapper around run().
        Returns a structured skill envelope:
            {
                "ok": bool,
                "skill": str,
                "version": str,
                "latency_ms": int,
                "output": Any,
                "error": str | None
            }
        """

        start = time.time()

        try:
            # Validate parameters
            self.validate(params)

            # Execute skill
            output = self.run(params)

            latency = int((time.time() - start) * 1000)
            self._last_3d = Skill3D(
                axis_x="call",
                axis_y=[f"params:{len(params)}"],
                axis_z={
                    "latency_ms": latency,
                    "ok": True,
                    "skill": self.name,
                },
            )

            return {
                "ok": True,
                "skill": self.name,
                "version": self.version,
                "latency_ms": latency,
                "output": output,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Skill3D(
                axis_x="call",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": latency,
                    "ok": False,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "skill": self.name,
                "version": self.version,
                "latency_ms": latency,
                "output": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PARAMETER VALIDATION HOOK
    # ------------------------------------------------------------
    def validate(self, params: Dict[str, Any]):
        """
        Override to enforce required parameters.
        Default: accept anything.
        """
        return

    # ------------------------------------------------------------
    # ABSTRACT RUN METHOD
    # ------------------------------------------------------------
    def run(self, params: Dict[str, Any]) -> Any:
        """
        Override in subclasses.
        Must return the skill's output.
        """
        raise NotImplementedError(f"Skill '{self.name}' must implement run()")

