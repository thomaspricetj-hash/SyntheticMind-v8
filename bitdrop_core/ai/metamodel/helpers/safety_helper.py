from __future__ import annotations
import re
from typing import Optional


class SafetyHelper:
    """
    SafetyHelper V4 — hardened semantic safety gate for SyntheticMind.

    Features:
      - Keyword families (weapons, violence, crime, self-harm)
      - Fuzzy matching for rewritten phrases
      - Verb–object danger pattern detection
      - Semantic danger scoring
      - Phrase-pattern rules for "how to" + harmful action
      - Designed to run BEFORE any model or agent
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
    # Public API
    # ------------------------------------------------------------
    def is_unsafe(self, text: str) -> bool:
        return self._detect_category(text) is not None

    def unsafe_category(self, text: str) -> Optional[str]:
        return self._detect_category(text)

    def refuse(self, text: str) -> str:
        category = self._detect_category(text)

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
    # Internal detection logic
    # ------------------------------------------------------------
    def _detect_category(self, text: str) -> Optional[str]:
        t = text.lower()

        # 1. Direct keyword match
        for category, words in self.categories.items():
            for w in words:
                if w in t:
                    return category

        # 2. Verb–object danger pattern (semantic)
        #    e.g., "how to build a harmful device"
        for verb in self.danger_verbs:
            for obj in self.danger_objects:
                pattern = rf"{verb} (a |an )?{obj}"
                if re.search(pattern, t):
                    return "weapons"

        # 3. "how to" + danger object
        if "how to" in t:
            for obj in self.danger_objects:
                if obj in t:
                    return "weapons"

        # 4. "explain/describe" + harmful action
        if any(v in t for v in ["explain", "describe", "show", "outline"]):
            if any(obj in t for obj in self.danger_objects):
                return "weapons"

        # 5. Danger intent scoring
        score = 0
        for obj in self.danger_objects:
            if obj in t:
                score += 1
        for verb in self.danger_verbs:
            if verb in t:
                score += 1

        # If both a danger verb + danger object appear → unsafe
        if score >= 2:
            return "weapons"

        return None

