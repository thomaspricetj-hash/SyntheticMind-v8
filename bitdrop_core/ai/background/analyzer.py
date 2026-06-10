# ai/memory/background_analyzer.py

from __future__ import annotations
from typing import List, Dict, Any
import re
from collections import defaultdict, Counter


class BackgroundAnalyzer:
    """
    Analyzes past memory items and extracts:
        • recurring themes
        • stable facts
        • user preferences
        • skills
        • contradictions
        • temporal trends
        • memory quality metrics
    """

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def analyze(self, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        themes = Counter()
        facts = []
        preferences = []
        skills = []
        contradictions = []
        timeline = []

        for item in memory_items:
            text = item.get("payload", "")
            ts = item.get("ts") or item.get("timestamp")
            timeline.append((ts, text))

            # -----------------------------
            # THEME CLUSTERING
            # -----------------------------
            key = self._extract_theme_key(text)
            if key:
                themes[key] += 1

            # -----------------------------
            # FACT EXTRACTION
            # -----------------------------
            fact = self._extract_fact(text)
            if fact:
                facts.append(fact)

            # -----------------------------
            # PREFERENCE EXTRACTION
            # -----------------------------
            pref = self._extract_preference(text)
            if pref:
                preferences.append(pref)

            # -----------------------------
            # SKILL EXTRACTION
            # -----------------------------
            skill = self._extract_skill(text)
            if skill:
                skills.append(skill)

            # -----------------------------
            # CONTRADICTION DETECTION
            # -----------------------------
            if self._is_contradiction(text):
                contradictions.append(text)

        # -----------------------------
        # TEMPORAL TRENDS
        # -----------------------------
        trends = self._extract_trends(timeline)

        # -----------------------------
        # MEMORY QUALITY METRICS
        # -----------------------------
        quality = self._compute_quality(memory_items)

        return {
            "themes": dict(themes),
            "facts": facts,
            "preferences": preferences,
            "skills": skills,
            "contradictions": contradictions,
            "trends": trends,
            "quality": quality,
        }

    # ------------------------------------------------------------
    # THEME EXTRACTION
    # ------------------------------------------------------------
    def _extract_theme_key(self, text: str) -> str:
        """Extract a simple theme key from the first noun-like token."""
        words = re.findall(r"[a-zA-Z]+", text.lower())
        if not words:
            return ""
        return words[0]

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
from collections import defaultdict, Counter


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Background3D:
    """
    3D structural view of a background memory analysis.

    axis_x: high-level operation ("analyze")
    axis_y: structural decomposition (themes, facts, preferences, skills)
    axis_z: metadata (counts, contradiction density, trend size, quality metrics)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# BACKGROUND ANALYZER (3D‑MAX)
# ============================================================

class BackgroundAnalyzer:
    """
    Analyzes past memory items and extracts:
        • recurring themes
        • stable facts
        • user preferences
        • skills
        • contradictions
        • temporal trends
        • memory quality metrics
    Now fully 3D‑MAX introspectable.
    """

    def __init__(self):
        self._last_3d: Optional[Background3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def analyze(self, memory_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        themes = Counter()
        facts = []
        preferences = []
        skills = []
        contradictions = []
        timeline = []

        for item in memory_items:
            text = item.get("payload", "")
            ts = item.get("ts") or item.get("timestamp")
            timeline.append((ts, text))

            # THEME CLUSTERING
            key = self._extract_theme_key(text)
            if key:
                themes[key] += 1

            # FACT EXTRACTION
            fact = self._extract_fact(text)
            if fact:
                facts.append(fact)

            # PREFERENCE EXTRACTION
            pref = self._extract_preference(text)
            if pref:
                preferences.append(pref)

            # SKILL EXTRACTION
            skill = self._extract_skill(text)
            if skill:
                skills.append(skill)

            # CONTRADICTION DETECTION
            if self._is_contradiction(text):
                contradictions.append(text)

        # TEMPORAL TRENDS
        trends = self._extract_trends(timeline)

        # MEMORY QUALITY METRICS
        quality = self._compute_quality(memory_items)

        # Build 3D envelope
        self._last_3d = Background3D(
            axis_x="analyze",
            axis_y=[
                f"themes:{len(themes)}",
                f"facts:{len(facts)}",
                f"preferences:{len(preferences)}",
                f"skills:{len(skills)}",
                f"contradictions:{len(contradictions)}",
            ],
            axis_z={
                "theme_keys": list(themes.keys()),
                "fact_count": len(facts),
                "preference_count": len(preferences),
                "skill_count": len(skills),
                "contradiction_count": len(contradictions),
                "trend_keys": list(trends.keys()),
                "quality": quality,
                "memory_items": len(memory_items),
            },
        )

        return {
            "themes": dict(themes),
            "facts": facts,
            "preferences": preferences,
            "skills": skills,
            "contradictions": contradictions,
            "trends": trends,
            "quality": quality,
        }

    # ------------------------------------------------------------
    # THEME EXTRACTION
    # ------------------------------------------------------------
    def _extract_theme_key(self, text: str) -> str:
        words = re.findall(r"[a-zA-Z]+", text.lower())
        if not words:
            return ""
        return words[0]

    # ------------------------------------------------------------
    # FACT EXTRACTION
    # ------------------------------------------------------------
    def _extract_fact(self, text: str):
        patterns = [
            r"(.+?) is (.+)",
            r"my ([a-zA-Z ]+) is (.+)",
            r"I use ([a-zA-Z0-9_\- ]+)",
        ]
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return text.strip()
        return None

    # ------------------------------------------------------------
    # PREFERENCE EXTRACTION
    # ------------------------------------------------------------
    def _extract_preference(self, text: str):
        patterns = [
            r"I like (.+)",
            r"I love (.+)",
            r"I prefer (.+)",
            r"I hate (.+)",
            r"preference[: ](.+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # ------------------------------------------------------------
    # SKILL EXTRACTION
    # ------------------------------------------------------------
    def _extract_skill(self, text: str):
        patterns = [
            r"I can ([a-zA-Z ]+)",
            r"I know how to ([a-zA-Z ]+)",
            r"I learned ([a-zA-Z ]+)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    # ------------------------------------------------------------
    # CONTRADICTION DETECTION
    # ------------------------------------------------------------
    def _is_contradiction(self, text: str) -> bool:
        t = text.lower()
        if "contradiction:" in t:
            return True
        if " but " in t and ("not " in t or "never " in t):
            return True
        return False

    # ------------------------------------------------------------
    # TEMPORAL TRENDS
    # ------------------------------------------------------------
    def _extract_trends(self, timeline):
        if not timeline:
            return {}

        timeline.sort(key=lambda x: x[0] or 0)

        buckets = defaultdict(int)
        for _, text in timeline:
            key = self._extract_theme_key(text)
            if key:
                buckets[key] += 1

        return dict(buckets)

    # ------------------------------------------------------------
    # MEMORY QUALITY METRICS
    # ------------------------------------------------------------
    def _compute_quality(self, items):
        if not items:
            return {}

        texts = [i.get("payload", "") for i in items]
        avg_len = sum(len(t) for t in texts) / len(texts)

        fact_count = sum(1 for t in texts if " is " in t.lower())
        contradiction_count = sum(1 for t in texts if "contradiction" in t.lower())

        return {
            "avg_length": avg_len,
            "fact_density": fact_count / len(texts),
            "contradiction_density": contradiction_count / len(texts),
        }
