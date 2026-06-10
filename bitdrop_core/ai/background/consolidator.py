# ai/memory/background_consolidator.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class BackgroundConsolidation3D:
    """
    3D structural view of a background consolidation cycle.

    axis_x: high-level operation ("consolidate")
    axis_y: structural decomposition (themes, facts, prefs, skills, contradictions)
    axis_z: metadata (counts, timestamps, quality summary)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# BACKGROUND CONSOLIDATOR (3D‑MAX)
# ============================================================

class BackgroundConsolidator:
    """
    Consolidates extracted insights into long‑term memory.
    Features:
        • deduplication
        • semantic fact promotion
        • structured tagging
        • contradiction logging
        • theme weighting
        • confidence scoring
    Now 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self._last_3d: Optional[BackgroundConsolidation3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def consolidate(self, insights: Dict[str, Any]):
        """
        Consolidate insights into:
            • episodic memory (structured)
            • semantic memory (facts)
            • vector memory (for retrieval)
        """
        start = time.time()

        themes = insights.get("themes", {})
        facts = insights.get("facts", [])
        prefs = insights.get("preferences", [])
        skills = insights.get("skills", [])
        contradictions = insights.get("contradictions", [])
        trends = insights.get("trends", {})
        quality = insights.get("quality", {})

        # THEMES
        self._store_themes(themes)

        # FACTS
        self._store_facts(facts)

        # PREFERENCES
        self._store_preferences(prefs)

        # SKILLS
        self._store_skills(skills)

        # CONTRADICTIONS
        self._store_contradictions(contradictions)

        # TRENDS
        self._store_trends(trends)

        # QUALITY METRICS
        self._store_quality(quality)

        # 3D envelope
        latency_ms = int((time.time() - start) * 1000)
        self._last_3d = BackgroundConsolidation3D(
            axis_x="consolidate",
            axis_y=[
                f"themes:{len(themes)}",
                f"facts:{len(facts)}",
                f"preferences:{len(prefs)}",
                f"skills:{len(skills)}",
                f"contradictions:{len(contradictions)}",
            ],
            axis_z={
                "latency_ms": latency_ms,
                "trend_keys": list(trends.keys()),
                "has_quality": bool(quality),
                "quality": dict(quality),
            },
        )

    # ------------------------------------------------------------
    # THEMES
    # ------------------------------------------------------------
    def _store_themes(self, themes: Dict[str, int]):
        for theme, count in themes.items():
            key = f"theme:{theme}"
            value = f"occurrences:{count}"

            self.runtime.memory.semantic.set(
                key, value, overwrite=True, confidence=0.8
            )

            self.runtime.memory.remember(
                f"[theme] {theme} occurred {count} times"
            )

    # ------------------------------------------------------------
    # FACTS
    # ------------------------------------------------------------
    def _store_facts(self, facts: List[str]):
        for fact in facts:
            key = f"fact:{hash(fact)}"
            self.runtime.memory.semantic.set(
                key, fact, overwrite=False, confidence=0.95
            )
            self.runtime.memory.remember(f"[fact] {fact}")

    # ------------------------------------------------------------
    # PREFERENCES
    # ------------------------------------------------------------
    def _store_preferences(self, prefs: List[str]):
        for pref in prefs:
            key = f"preference:{pref.lower()}"
            self.runtime.memory.semantic.set(
                key, "true", overwrite=True, confidence=0.9
            )
            self.runtime.memory.remember(f"[preference] {pref}")

    # ------------------------------------------------------------
    # SKILLS
    # ------------------------------------------------------------
    def _store_skills(self, skills: List[str]):
        for skill in skills:
            key = f"skill:{skill.lower()}"
            self.runtime.memory.semantic.set(
                key, "learned", overwrite=True, confidence=0.85
            )
            self.runtime.memory.remember(f"[skill] {skill}")

    # ------------------------------------------------------------
    # CONTRADICTIONS
    # ------------------------------------------------------------
    def _store_contradictions(self, contradictions: List[str]):
        for c in contradictions:
            key = f"contradiction:{hash(c)}"
            self.runtime.memory.semantic.set(
                key, c, overwrite=True, confidence=0.5
            )
            self.runtime.memory.remember(f"[contradiction] {c}")

    # ------------------------------------------------------------
    # TRENDS
    # ------------------------------------------------------------
    def _store_trends(self, trends: Dict[str, int]):
        for theme, count in trends.items():
            self.runtime.memory.remember(
                f"[trend] {theme} trending with {count} mentions"
            )

    # ------------------------------------------------------------
    # QUALITY METRICS
    # ------------------------------------------------------------
    def _store_quality(self, quality: Dict[str, Any]):
        if not quality:
            return

        summary = (
            f"[quality] avg_length={quality.get('avg_length')}, "
            f"fact_density={quality.get('fact_density')}, "
            f"contradiction_density={quality.get('contradiction_density')}"
        )

        self.runtime.memory.remember(summary)


