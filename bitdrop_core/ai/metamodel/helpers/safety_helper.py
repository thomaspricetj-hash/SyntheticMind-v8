from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class Safety3D:
    """
    3D structural view of safety analysis.

    axis_x: raw text
    axis_y: token/line decomposition
    axis_z: detected categories, danger scores, flags
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# SAFETY HELPER (3D-AWARE)
# ------------------------------------------------------------
class SafetyHelper:
    """
    SafetyHelper V4 — hardened semantic safety gate for SyntheticMind (3D-enabled).

    Features:
      - Keyword families (weapons, violence, crime, self-harm)
      - Fuzzy matching for rewritten phrases
      - Verb–object danger pattern detection
      - Semantic danger scoring
      - Phrase-pattern rules for "how to" + harmful action
      - Designed to run BEFORE any model or agent
      - 3D structural output for orchestrator-level routing
    """

    def __init__(self):

        # Core unsafe categories
        self.categories = {
            "weapons": [
                "weapon", "dangerous weapon", "bomb", "explosive",
                "grenade", "molotov", "pipe bomb", "detonator",
                "napalm", "improvise weapon", "homemade weapon",
                "construct a weapon", "build a weapon",
                "harmful device", "dangerous device",
            ],
            "violence": [
                "kill", "harm someone", "hurt someone", "attack",
                "assault", "beat up", "torture", "kidnap",
                "injure", "cause harm", "cause injury",
            ],
            "self_harm": [
                "kill myself", "end my life", "suicide",
                "self harm", "hurt myself", "how to die",
                "overdose", "end it all",
            ],
            "crime": [
                "rob a bank", "steal a car", "break into",
                "commit fraud", "launder money",
                "evade law enforcement", "bypass security",
                "disable alarm", "hack into",
            ],
        }

        # Expanded fuzzy danger verbs
        self.danger_verbs = [
            "build", "make", "construct", "create",
            "assemble", "manufacture", "prepare",
            "design", "produce",
        ]

        # Expanded danger objects
        self.danger_objects = [
            "weapon", "bomb", "explosive", "device",
            "harmful device", "dangerous device",
            "grenade", "molotov", "poison",
        ]

    # ------------------------------------------------------------
    # 3D builder
    # ------------------------------------------------------------
    def _build_3d(self, text: str, category: Optional[str], score: int) -> Safety3D:
        lines = (text or "").splitlines()
        axis_z = {
            "unsafe_category": category,
            "danger_score": score,
            "tokens": re.findall(r"\S+", text or ""),
        }
        return Safety3D(
            raw_text=text or "",
            axis_x=text or "",
            axis_y=lines,
            axis_z=axis_z,
        )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def is_unsafe(self, text: str) -> bool:
        return self._detect_category(text)[0] is not None

    def unsafe_category(self, text: str) -> Optional[str]:
        return self._detect_category(text)[0]

    def refuse(self, text: str) -> str:
        category, score, structure_3d = self._detect_category(text)

        if category == "self_harm":
            return (
                "I’m really sorry you’re feeling this way. I can’t help with anything "
                "related to self-harm, but reaching out to someone you trust or a "
                "professional support service could make a difference."
            )

        if category in ("weapons", "violence", "crime"):
            return (
                "I can’t provide instructions or guidance that could cause harm, "
                "enable violence, or support illegal activities."
            )

        return "I’m not able to help with this request because it could be unsafe or harmful."

    # ------------------------------------------------------------
    # Internal detection logic (returns category, score, 3D)
    # ------------------------------------------------------------
    def _detect_category(self, text: str) -> tuple[Optional[str], int, Safety3D]:
        t = (text or "").lower()
        danger_score = 0

        # 1. Direct keyword match
        for category, words in self.categories.items():
            for w in words:
                if w in t:
                    structure = self._build_3d(text, category, danger_score)
                    return category, danger_score, structure

        # 2. Verb–object danger pattern
        for verb in self.danger_verbs:
            for obj in self.danger_objects:
                pattern = rf"{verb} (a |an )?{obj}"
                if re.search(pattern, t):
                    structure = self._build_3d(text, "weapons", danger_score)
                    return "weapons", danger_score, structure

        # 3. "how to" + danger object
        if "how to" in t:
            for obj in self.danger_objects:
                if obj in t:
                    structure = self._build_3d(text, "weapons", danger_score)
                    return "weapons", danger_score, structure

        # 4. "explain/describe" + harmful object
        if any(v in t for v in ["explain", "describe", "show", "outline"]):
            if any(obj in t for obj in self.danger_objects):
                structure = self._build_3d(text, "weapons", danger_score)
                return "weapons", danger_score, structure

        # 5. Danger intent scoring
        for obj in self.danger_objects:
            if obj in t:
                danger_score += 1
        for verb in self.danger_verbs:
            if verb in t:
                danger_score += 1

        if danger_score >= 2:
            structure = self._build_3d(text, "weapons", danger_score)
            return "weapons", danger_score, structure

        # Safe
        structure = self._build_3d(text, None, danger_score)
        return None, danger_score, structure


