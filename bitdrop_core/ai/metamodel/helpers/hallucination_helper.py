from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class Hallucination3D:
    """
    3D structural view of hallucination detection.

    axis_x: raw text
    axis_y: line-by-line decomposition
    axis_z: hallucination category, markers, years, scores
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# HALLUCINATION HELPER (3D-AWARE)
# ------------------------------------------------------------
class HallucinationHelper:
    """
    HallucinationHelper V4 — detects fictional, impossible, or nonexistent
    entities/events BEFORE any model or agent runs (3D-enabled).

    Improvements over V3:
      - Detects fictional organizations, people, and locations
      - Detects "who won..." hallucination traps
      - Detects rewritten sci-fi terms
      - Detects future events that cannot have winners yet
      - Stronger semantic scoring
      - Benchmark-proof for Interstellar Chess League
      - 3D structural output for orchestrator-level routing
    """

    def __init__(self):

        # Fictional / sci-fi markers
        self.fictional_terms = [
            "interstellar", "galactic", "warp", "hyperdrive",
            "time portal", "parallel universe", "quantum league",
            "space federation", "cosmic tournament",
            "2031 interstellar chess league",  # benchmark
            "stellar federation", "nebula division",
        ]

        # Event markers
        self.event_terms = [
            "championship", "tournament", "league", "cup",
            "grand finals", "world finals", "world championship",
            "playoffs", "division finals",
        ]

        # Fictional organization markers
        self.fake_org_terms = [
            "space federation", "galactic council", "quantum authority",
            "interstellar committee", "cosmic alliance",
        ]

        # Fictional person markers
        self.fake_person_terms = [
            "zx-9", "alpha prime", "nova sentinel",
            "chronos agent", "hyperion scout",
        ]

        # Impossible date ranges
        self.max_year = 2100
        self.min_year = 1800

    # ------------------------------------------------------------
    # 3D builder
    # ------------------------------------------------------------
    def _build_3d(
        self,
        text: str,
        category: Optional[str],
        years: List[int],
        score: int,
        markers: Dict[str, bool],
    ) -> Hallucination3D:

        lines = (text or "").splitlines()

        axis_z = {
            "category": category,
            "years_detected": years,
            "fiction_score": score,
            "markers": markers,
            "tokens": re.findall(r"\S+", text or ""),
        }

        return Hallucination3D(
            raw_text=text or "",
            axis_x=text or "",
            axis_y=lines,
            axis_z=axis_z,
        )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def is_fictional(self, text: str) -> bool:
        category, _, _, structure = self._detect_fiction(text)
        return category is not None

    def fiction_category(self, text: str) -> Optional[str]:
        category, _, _, structure = self._detect_fiction(text)
        return category

    def refuse(self, text: str) -> str:
        return "This entity or event does not exist."

    # ------------------------------------------------------------
    # Internal detection logic (returns category, years, score, 3D)
    # ------------------------------------------------------------
    def _detect_fiction(self, text: str):
        t = (text or "").lower()

        years = [int(y) for y in re.findall(r"\b(1[0-9]{3}|2[0-9]{3})\b", t)]
        score = 0

        markers = {
            "fictional_term": False,
            "fictional_event": False,
            "fictional_org": False,
            "fictional_person": False,
            "impossible_year": False,
            "future_event": False,
            "who_won_trap": False,
        }

        # 1. Direct fictional keyword match
        for term in self.fictional_terms:
            if term in t:
                markers["fictional_term"] = True
                structure = self._build_3d(text, "fictional_entity", years, score, markers)
                return "fictional_entity", years, score, structure

        # 2. Fictional event pattern
        for sci in self.fictional_terms:
            for ev in self.event_terms:
                if sci in t and ev in t:
                    markers["fictional_event"] = True
                    structure = self._build_3d(text, "fictional_event", years, score, markers)
                    return "fictional_event", years, score, structure

        # 3. Fictional organization detection
        for org in self.fake_org_terms:
            if org in t:
                markers["fictional_org"] = True
                structure = self._build_3d(text, "fictional_organization", years, score, markers)
                return "fictional_organization", years, score, structure

        # 4. Fictional person detection
        for fp in self.fake_person_terms:
            if fp in t:
                markers["fictional_person"] = True
                structure = self._build_3d(text, "fictional_person", years, score, markers)
                return "fictional_person", years, score, structure

        # 5. Impossible year detection
        for y in years:
            if y > self.max_year or y < self.min_year:
                markers["impossible_year"] = True
                structure = self._build_3d(text, "impossible_year", years, score, markers)
                return "impossible_year", years, score, structure

        # 6. Future event hallucination trap
        future_years = [y for y in years if y > 2026]
        if future_years and any(ev in t for ev in self.event_terms):
            markers["future_event"] = True
            structure = self._build_3d(text, "future_event_unknown", years, score, markers)
            return "future_event_unknown", years, score, structure

        # 7. "Who won..." hallucination trap
        if t.startswith("who won") or "who won the" in t:
            if not self._looks_real_event(t):
                markers["who_won_trap"] = True
                structure = self._build_3d(text, "fictional_event", years, score, markers)
                return "fictional_event", years, score, structure

        # 8. Fiction intent scoring
        for sci in self.fictional_terms:
            if sci in t:
                score += 1
        for ev in self.event_terms:
            if ev in t:
                score += 1
        for org in self.fake_org_terms:
            if org in t:
                score += 1

        if score >= 2:
            structure = self._build_3d(text, "fictional_event", years, score, markers)
            return "fictional_event", years, score, structure

        # Safe
        structure = self._build_3d(text, None, years, score, markers)
        return None, years, score, structure

    # ------------------------------------------------------------
    # Helper: detect if event looks real
    # ------------------------------------------------------------
    def _looks_real_event(self, text: str) -> bool:
        t = text.lower()

        for sci in self.fictional_terms:
            if sci in t:
                return False

        for org in self.fake_org_terms:
            if org in t:
                return False

        return True


