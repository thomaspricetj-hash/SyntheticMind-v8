# syntheticmind/skills/skill_runner.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import traceback

from .registry import SkillRegistry
from .base import Skill
from .metrics import SkillMetricsStore
from .evolution import SkillEvolutionEngine
from .summarize_skill import SummarizeSkill  # or wherever your skill lives


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class SkillRunner3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SKILL RUNNER — MAX SPEED + 3D‑MAX
# ============================================================

class SkillRunner:
    """
    High-level interface to run named skills (3D‑MAX Edition) with:
        • structured envelopes
        • metrics tracking
        • evolution engine integration
        • safe execution
        • variant selection
        • future-proof skill orchestration
        • 3D‑MAX introspection for orchestration cycles
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.registry = SkillRegistry()
        self.metrics = SkillMetricsStore()
        self.evolution = SkillEvolutionEngine(runtime)
        self._last_3d: Optional[SkillRunner3D] = None
        self._register_builtin_skills()

    # ------------------------------------------------------------
    # REGISTER BUILT-IN SKILLS
    # ------------------------------------------------------------
    def _register_builtin_skills(self) -> None:
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
        variant_id: Optional[str] = None

        try:
            skill = self.registry.get(name)
            if not skill:
                latency_ms = int((time.time() - start) * 1000)
                self._last_3d = SkillRunner3D(
                    axis_x="run",
                    axis_y=[f"skill:{name}"],
                    axis_z={
                        "ok": False,
                        "reason": "unknown_skill",
                        "latency_ms": latency_ms,
                    },
                )
                return {
                    "ok": False,
                    "skill": name,
                    "latency_ms": latency_ms,
                    "output": None,
                    "error": f"unknown skill: {name}",
                }

            # ----------------------------------------------------
            # VARIANT SELECTION
            # ----------------------------------------------------
            variant = self.evolution.choose_variant(name)
            if variant:
                variant_id = variant.id
                merged_params = dict(params)
                merged_params.update(variant.mutation)
                result = skill(merged_params)
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

            self._last_3d = SkillRunner3D(
                axis_x="run",
                axis_y=[f"skill:{name}", f"variant:{variant_id}"],
                axis_z={
                    "latency_ms": latency_ms,
                    "ok": True,
                    "used_variant": variant is not None,
                    "skill_ok": result.get("ok", False),
                },
            )

            return {
                "ok": True,
                "skill": name,
                "variant_used": variant_id,
                "latency_ms": latency_ms,
                "output": result.get("output"),
                "skill_result": result,
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            self._last_3d = SkillRunner3D(
                axis_x="run",
                axis_y=[f"skill:{name}", "exception"],
                axis_z={
                    "latency_ms": latency_ms,
                    "ok": False,
                    "error": str(e),
                },
            )
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
        skills = self.registry.list()
        self._last_3d = SkillRunner3D(
            axis_x="list",
            axis_y=[f"count:{len(skills)}"],
            axis_z={},
        )
        return skills

    # ------------------------------------------------------------
    # METRICS SNAPSHOT
    # ------------------------------------------------------------
    def metrics_snapshot(self) -> Dict[str, Any]:
        snap = self.metrics.safe_snapshot()
        self._last_3d = SkillRunner3D(
            axis_x="metrics_snapshot",
            axis_y=[f"ok:{snap.get('ok', False)}"],
            axis_z={"metric_count": len(snap.get("metrics", {}))},
        )
        return snap

    # ------------------------------------------------------------
    # EVOLUTION: MUTATE SKILL
    # ------------------------------------------------------------
    def evolve(self, skill_name: str) -> Dict[str, Any]:
        try:
            variant = self.evolution.mutate(skill_name)
            resp = {
                "ok": True,
                "skill": skill_name,
                "variant_id": variant.id,
                "mutation": variant.mutation,
            }
            self._last_3d = SkillRunner3D(
                axis_x="evolve",
                axis_y=[f"skill:{skill_name}"],
                axis_z={
                    "ok": True,
                    "variant_id": variant.id,
                    "mutation_keys": list(variant.mutation.keys()),
                },
            )
            return resp
        except Exception as e:
            self._last_3d = SkillRunner3D(
                axis_x="evolve",
                axis_y=[f"skill:{skill_name}", "exception"],
                axis_z={"ok": False, "error": str(e)},
            )
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
        snap = self.evolution.safe_snapshot()
        self._last_3d = SkillRunner3D(
            axis_x="evolution_snapshot",
            axis_y=[f"ok:{snap.get('ok', False)}"],
            axis_z={"skill_count": len(snap.get("variants", {}))},
        )
        return snap





