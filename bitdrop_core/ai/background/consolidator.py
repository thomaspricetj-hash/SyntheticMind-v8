# ai/memory/background_consolidator.py

from __future__ import annotations
from typing import Dict, Any, List
import time


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
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

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

        # THEMES
        self._store_themes(insights.get("themes", {}))

        # FACTS
        self._store_facts(insights.get("facts", []))

        # PREFERENCES
        self._store_preferences(insights.get("preferences", []))

        # SKILLS
        self._store_skills(insights.get("skills", []))

        # CONTRADICTIONS
        self._store_contradictions(insights.get("contradictions", []))

        # TRENDS
        self._store_trends(insights.get("trends", {}))

        # QUALITY METRICS
        self._store_quality(insights.get("quality", {}))

    # ------------------------------------------------------------
    # THEMES
    # ------------------------------------------------------------
    def _store_themes(self, themes: Dict[str, int]):
        for theme, count in themes.items():
            key = f"theme:{theme}"
            value = f"occurrences:{count}"

            # semantic memory: stable fact
            self.runtime.memory.semantic.set(
                key, value, overwrite=True, confidence=0.8
            )

            # episodic memory: summary
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

