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

    # ------------------------------------------------------------
    # CHOOSE BEST VARIANT
    # ------------------------------------------------------------
    def choose_variant(self, skill_name: str) -> Optional[SkillVariant]:
        """
        Select the best variant based on health score.
        """

        variants = self.variants.get(skill_name, {})
        if not variants:
            return None

        return max(variants.values(), key=lambda v: v.health)

    # ------------------------------------------------------------
    # RECORD PERFORMANCE
    # ------------------------------------------------------------
    def record_variant_call(self, skill_name: str, variant_id: str, latency_ms: int, ok: bool):
        v = self.variants.get(skill_name, {}).get(variant_id)
        if v:
            v.record(latency_ms, ok)

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

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of all variants.
        """

        out = {}
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
        return out

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def safe_snapshot(self) -> Dict[str, Any]:
        try:
            return {
                "ok": True,
                "variants": self.snapshot(),
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "variants": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

