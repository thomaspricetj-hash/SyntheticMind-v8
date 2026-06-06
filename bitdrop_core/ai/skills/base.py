# syntheticmind/skills/skill.py

from __future__ import annotations
from typing import Any, Dict
import time
import traceback


class Skill:
    """
    Base class for reusable skills.
    A skill is a named, parameterized workflow.

    Provides:
        • structured envelopes
        • latency measurement
        • safe execution wrapper
        • parameter validation hook
        • evolution metadata
        • future-proof interface for SkillRegistry + SkillRunner
    """

    # ------------------------------------------------------------
    # METADATA
    # ------------------------------------------------------------
    name: str = "base-skill"
    description: str = "Base skill"
    version: str = "1.0.0"

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

            return {
                "ok": True,
                "skill": self.name,
                "version": self.version,
                "latency_ms": int((time.time() - start) * 1000),
                "output": output,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "skill": self.name,
                "version": self.version,
                "latency_ms": int((time.time() - start) * 1000),
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
