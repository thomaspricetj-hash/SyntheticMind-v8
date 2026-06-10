# syntheticmind/skills/skill_evolution_engine.py

from __future__ import annotations
from typing import Dict, Any, Optional
import uuid
import time
import traceback


class SkillVariant:
    """
    Represents a mutated variant of a skill.
    Tracks:
        • mutation metadata
        • performance metrics
        • lineage
        • health score
    """

    def __init__(self, base_name: str, mutation: Dict[str, Any], parent_id: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.base_name = base_name
        self.parent_id = parent_id
        self.mutation = mutation

        # Metrics
        self.calls = 0
        self.total_latency_ms = 0
        self.failures = 0

        # Evolution metadata
        self.created_at = time.time()
        self.last_used = None

    # ------------------------------------------------------------
    def record(self, latency_ms: int, ok: bool):
        self.calls += 1
        self.total_latency_ms += latency_ms
        self.last_used = time.time()
        if not ok:
            self.failures += 1

    # ------------------------------------------------------------
    @property
    def avg_latency(self) -> float:
        return self.total_latency_ms / self.calls if self.calls else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.calls if self.calls else 0.0

    @property
    def health(self) -> float:
        """
        Composite health score:
            lower latency → better
            lower failure rate → better
        """
        return max(0.0, 1.0 - (self.avg_latency / 2000) - (self.failure_rate * 2))


# ======================================================================
# EVOLUTION ENGINE
# ======================================================================

class SkillEvolutionEngine:
    """
    Generates, evaluates, and evolves skill variants.
    Provides:
        • structured envelopes
        • multi-strategy mutation
        • variant scoring
        • survival/retirement logic
        • lineage tracking
        • safe execution
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        # base_skill_name -> {variant_id -> SkillVariant}
        self.variants: Dict[str, Dict[str, SkillVariant]] = {}

    # ------------------------------------------------------------
    # MUTATION
    # ------------------------------------------------------------
    def mutate(self, skill_name: str, parent_id: Optional[str] = None) -> SkillVariant:
        """
        Create a mutation for a skill.
        Mutation strategies can be expanded.
        """

        mutation = {
            "prompt_prefix": "Be more concise and structured.\n",
            "temperature_boost": 0.1,
            "format_hint": "Use bullet points when possible.",
        }

        variant = SkillVariant(skill_name, mutation, parent_id)
        self.variants.setdefault(skill_name, {})[variant.id] = variant
        return variant
# syntheticmind/skills/skill_evolution_engine.py


from dataclasses import dataclass
from typing import Dict, Any, Optional
import uuid
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURES
# ============================================================

@dataclass
class SkillVariant3D:
    axis_x: str
    axis_y: list
    axis_z: dict


@dataclass
class Evolution3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SKILL VARIANT
# ============================================================

class SkillVariant:
    """
    Represents a mutated variant of a skill.
    Tracks:
        • mutation metadata
        • performance metrics
        • lineage
        • health score
    """

    def __init__(self, base_name: str, mutation: Dict[str, Any], parent_id: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.base_name = base_name
        self.parent_id = parent_id
        self.mutation = mutation

        # Metrics
        self.calls = 0
        self.total_latency_ms = 0
        self.failures = 0

        # Evolution metadata
        self.created_at = time.time()
        self.last_used: Optional[float] = None

        # 3D‑MAX
        self._last_3d: Optional[SkillVariant3D] = None

    # ------------------------------------------------------------
    def record(self, latency_ms: int, ok: bool):
        self.calls += 1
        self.total_latency_ms += latency_ms
        self.last_used = time.time()
        if not ok:
            self.failures += 1

        self._last_3d = SkillVariant3D(
            axis_x="record",
            axis_y=[f"ok:{ok}"],
            axis_z={
                "latency_ms": latency_ms,
                "calls": self.calls,
                "failures": self.failures,
                "health": self.health,
            },
        )

    # ------------------------------------------------------------
    @property
    def avg_latency(self) -> float:
        return self.total_latency_ms / self.calls if self.calls else 0.0

    @property
    def failure_rate(self) -> float:
        return self.failures / self.calls if self.calls else 0.0

    @property
    def health(self) -> float:
        """
        Composite health score:
            lower latency → better
            lower failure rate → better
        """
        return max(0.0, 1.0 - (self.avg_latency / 2000) - (self.failure_rate * 2))


# ======================================================================
# EVOLUTION ENGINE
# ======================================================================

class SkillEvolutionEngine:
    """
    Generates, evaluates, and evolves skill variants.
    Provides:
        • structured envelopes
        • multi-strategy mutation
        • variant scoring
        • survival/retirement logic
        • lineage tracking
        • safe execution
        • 3D‑MAX introspection
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        # base_skill_name -> {variant_id -> SkillVariant}
        self.variants: Dict[str, Dict[str, SkillVariant]] = {}
        self._last_3d: Optional[Evolution3D] = None

    # ------------------------------------------------------------
    # MUTATION
    # ------------------------------------------------------------
    def mutate(self, skill_name: str, parent_id: Optional[str] = None) -> SkillVariant:
        """
        Create a mutation for a skill.
        Mutation strategies can be expanded.
        """

        mutation = {
            "prompt_prefix": "Be more concise and structured.\n",
            "temperature_boost": 0.1,
            "format_hint": "Use bullet points when possible.",
        }

        variant = SkillVariant(skill_name, mutation, parent_id)
        self.variants.setdefault(skill_name, {})[variant.id] = variant

        self._last_3d = Evolution3D(
            axis_x="mutate",
            axis_y=[f"skill:{skill_name}"],
            axis_z={
                "variant_id": variant.id,
                "has_parent": parent_id is not None,
                "mutation_keys": list(mutation.keys()),
            },
        )

        return variant

    # ------------------------------------------------------------
    # CHOOSE BEST VARIANT
    # ------------------------------------------------------------
    def choose_variant(self, skill_name: str) -> Optional[SkillVariant]:
        """
        Select the best variant based on health score.
        """

        variants = self.variants.get(skill_name, {})
        if not variants:
            self._last_3d = Evolution3D(
                axis_x="choose_variant",
                axis_y=[f"skill:{skill_name}"],
                axis_z={"found": False, "count": 0},
            )
            return None

        best = max(variants.values(), key=lambda v: v.health)
        self._last_3d = Evolution3D(
            axis_x="choose_variant",
            axis_y=[f"skill:{skill_name}"],
            axis_z={
                "found": True,
                "count": len(variants),
                "best_variant_id": best.id,
                "best_health": best.health,
            },
        )
        return best

    # ------------------------------------------------------------
    # RECORD PERFORMANCE
    # ------------------------------------------------------------
    def record_variant_call(self, skill_name: str, variant_id: str, latency_ms: int, ok: bool):
        v = self.variants.get(skill_name, {}).get(variant_id)
        if v:
            v.record(latency_ms, ok)
            self._last_3d = Evolution3D(
                axis_x="record_variant_call",
                axis_y=[f"skill:{skill_name}", f"variant:{variant_id}"],
                axis_z={
                    "latency_ms": latency_ms,
                    "ok": ok,
                    "health": v.health,
                },
            )
        else:
            self._last_3d = Evolution3D(
                axis_x="record_variant_call",
                axis_y=[f"skill:{skill_name}", f"variant:{variant_id}"],
                axis_z={"missing": True},
            )

    # ------------------------------------------------------------
    # RETIRE BAD VARIANTS
    # ------------------------------------------------------------
    def retire_weak(self, skill_name: str, threshold: float = 0.2):
        """
        Remove variants with health below threshold.
        """

        variants = self.variants.get(skill_name, {})
        weak = [vid for vid, v in variants.items() if v.health < threshold]

        for vid in weak:
            del variants[vid]

        self._last_3d = Evolution3D(
            axis_x="retire_weak",
            axis_y=[f"skill:{skill_name}"],
            axis_z={
                "threshold": threshold,
                "removed": len(weak),
                "remaining": len(variants),
            },
        )

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of all variants.
        """

        out: Dict[str, Any] = {}
        for sname, vs in self.variants.items():
            out[sname] = {
                vid: {
                    "mutation": v.mutation,
                    "calls": v.calls,
                    "avg_latency": v.avg_latency,
                    "failure_rate": v.failure_rate,
                    "health": v.health,
                    "parent_id": v.parent_id,
                    "created_at": v.created_at,
                    "last_used": v.last_used,
                }
                for vid, v in vs.items()
            }

        self._last_3d = Evolution3D(
            axis_x="snapshot",
            axis_y=[f"skills:{len(out)}"],
            axis_z={"total_variants": sum(len(vs) for vs in self.variants.values())},
        )

        return out

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def safe_snapshot(self) -> Dict[str, Any]:
        try:
            variants = self.snapshot()
            return {
                "ok": True,
                "variants": variants,
                "error": None,
            }
        except Exception as e:
            self._last_3d = Evolution3D(
                axis_x="safe_snapshot",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return {
                "ok": False,
                "variants": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
