# syntheticmind/skills/skill_runner.py

from __future__ import annotations
from typing import Any, Dict
import time
import traceback

from .registry import SkillRegistry
from .base import Skill
from .metrics import SkillMetricsStore
from .evolution import SkillEvolutionEngine
from .summarize_skill import SummarizeSkill   # or wherever your skill lives


class SkillRunner:
    """
    High-level interface to run named skills with:
        • structured envelopes
        • metrics tracking
        • evolution engine integration
        • safe execution
        • variant selection
        • future-proof skill orchestration
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.registry = SkillRegistry()
        self.metrics = SkillMetricsStore()
        self.evolution = SkillEvolutionEngine(runtime)
        self._register_builtin_skills()

    # ------------------------------------------------------------
    # REGISTER BUILT-IN SKILLS
    # ------------------------------------------------------------
    def _register_builtin_skills(self):
        self.registry.register(SummarizeSkill(self.runtime))

    # ------------------------------------------------------------
    # RUN SKILL
    # ------------------------------------------------------------
    def run(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a skill with:
            • variant selection
            • mutation injection
            • metrics tracking
            • evolution tracking
            • structured envelope
        """

        start = time.time()

        try:
            skill = self.registry.get(name)
            if not skill:
                return {
                    "ok": False,
                    "skill": name,
                    "latency_ms": int((time.time() - start) * 1000),
                    "output": None,
                    "error": f"unknown skill: {name}",
                }

            # ----------------------------------------------------
            # VARIANT SELECTION
            # ----------------------------------------------------
            variant = self.evolution.choose_variant(name)

            if variant:
                merged_params = dict(params)
                merged_params.update(variant.mutation)
                result = skill(merged_params)  # Skill.__call__ → structured envelope
            else:
                result = skill(params)

            latency_ms = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # METRICS + EVOLUTION TRACKING
            # ----------------------------------------------------
            self.metrics.record(name, latency_ms, error=result.get("error"))

            if variant:
                self.evolution.record_variant_call(
                    name,
                    variant.id,
                    latency_ms,
                    ok=result.get("ok", False),
                )

            # ----------------------------------------------------
            # FINAL STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "skill": name,
                "variant_used": variant.id if variant else None,
                "latency_ms": latency_ms,
                "output": result.get("output"),
                "skill_result": result,
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            return {
                "ok": False,
                "skill": name,
                "latency_ms": latency_ms,
                "output": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # LIST SKILLS
    # ------------------------------------------------------------
    def list(self) -> Dict[str, Dict[str, Any]]:
        return self.registry.list()

    # ------------------------------------------------------------
    # METRICS SNAPSHOT
    # ------------------------------------------------------------
    def metrics_snapshot(self) -> Dict[str, Any]:
        return self.metrics.safe_snapshot()

    # ------------------------------------------------------------
    # EVOLUTION: MUTATE SKILL
    # ------------------------------------------------------------
    def evolve(self, skill_name: str) -> Dict[str, Any]:
        try:
            variant = self.evolution.mutate(skill_name)
            return {
                "ok": True,
                "skill": skill_name,
                "variant_id": variant.id,
                "mutation": variant.mutation,
            }
        except Exception as e:
            return {
                "ok": False,
                "skill": skill_name,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # EVOLUTION SNAPSHOT
    # ------------------------------------------------------------
    def evolution_snapshot(self) -> Dict[str, Any]:
        return self.evolution.safe_snapshot()





