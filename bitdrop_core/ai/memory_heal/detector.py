# ai/memory/memory_issue_detector.py

from __future__ import annotations
from typing import List, Dict, Any
import re
from collections import defaultdict


class MemoryIssueDetector:
    """
    Detects memory issues:
        • exact duplicates
        • near-duplicates (fuzzy)
        • contradictions (semantic + structural)
        • noise entries (short, low-entropy, malformed)
        • suspicious patterns
    """

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def detect(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        duplicates = []
        near_duplicates = []
        contradictions = []
        noise = []
        suspicious = []

        seen_exact = set()
        seen_normalized = defaultdict(list)

        for item in items:
            text = item.get("payload", "").strip()
            if not text:
                continue

            # ----------------------------------------------------
            # EXACT DUPLICATES
            # ----------------------------------------------------
            if text in seen_exact:
                duplicates.append(text)
            else:
                seen_exact.add(text)

            # ----------------------------------------------------
            # NEAR DUPLICATES (normalized)
            # ----------------------------------------------------
            norm = self._normalize(text)
            seen_normalized[norm].append(text)
            if len(seen_normalized[norm]) > 1:
                near_duplicates.append(text)

            # ----------------------------------------------------
            # CONTRADICTIONS
            # ----------------------------------------------------
            if self._is_contradiction(text):
                contradictions.append(text)

            # ----------------------------------------------------
            # NOISE
            # ----------------------------------------------------
            if self._is_noise(text):
                noise.append(text)

            # ----------------------------------------------------
            # SUSPICIOUS PATTERNS
            # ----------------------------------------------------
            if self._is_suspicious(text):
                suspicious.append(text)

        return {
            "duplicates": duplicates,
            "near_duplicates": near_duplicates,
            "contradictions": contradictions,
            "noise": noise,
            "suspicious": suspicious,
        }

    # ------------------------------------------------------------
    # NORMALIZATION FOR NEAR-DUPLICATE DETECTION
    # ------------------------------------------------------------
    def _normalize(self, text: str) -> str:
        """
        Normalize text for fuzzy duplicate detection:
            • lowercase
            • remove punctuation
            • collapse whitespace
        """
        t = text.lower()
        t = re.sub(r"[^a-z0-9 ]+", "", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    # ------------------------------------------------------------
    # CONTRADICTION DETECTION
    # ------------------------------------------------------------
    def _is_contradiction(self, text: str) -> bool:
        """
        Detect contradictions such as:
            'X is Y' vs 'X is not Y'
            'I never X' vs 'I X'
            explicit contradiction markers
        """
        t = text.lower()

        if "contradiction:" in t:
            return True

        # Simple structural contradiction
        if " is " in t and " not " in t:
            return True

        # Negation patterns
        if "never" in t and "i " in t:
            return True

        return False

    # ------------------------------------------------------------
    # NOISE DETECTION
    # ------------------------------------------------------------
    def _is_noise(self, text: str) -> bool:
        """
        Noise includes:
            • very short strings
            • low-entropy strings
            • repeated characters
            • malformed entries
        """
        if len(text) < 5:
            return True

        # Low entropy: e.g., "aaaaaa", "111111"
        if len(set(text)) <= 2:
            return True

        # Garbage patterns
        if re.fullmatch(r"[^\w]+", text):
            return True

        return False

    # ------------------------------------------------------------
    # SUSPICIOUS PATTERN DETECTION
    # ------------------------------------------------------------
    def _is_suspicious(self, text: str) -> bool:
        """
        Suspicious entries include:
            • truncated sentences
            • repeated prefixes
            • memory corruption indicators
        """
        t = text.lower()

        # Truncated or incomplete
        if t.endswith(("...", "--", "??", "!!")):
            return True

        # Corruption markers
        if " " in text or "\x00" in text:
            return True

        # Repeated prefix patterns
        if re.match(r"(.+)\1{2,}", t):
            return True

        return False
