from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
from collections import defaultdict


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class MemoryIssue3D:
    """
    3D structural view of a memory issue detection cycle.

    axis_x: raw items (stringified)
    axis_y: structural decomposition (payload types, lengths)
    axis_z: metadata (duplicates, near-duplicates, contradictions, noise, suspicious)
    """
    raw_items: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[MemoryIssue3D] = None


def _build_3d(items: List[Dict[str, Any]], report: Dict[str, Any]) -> MemoryIssue3D:
    axis_y = []
    for it in items:
        payload = it.get("payload", "")
        axis_y.append(f"{type(payload).__name__}:{len(str(payload))}")

    axis_z = {
        "duplicates": report.get("duplicates", []),
        "near_duplicates": report.get("near_duplicates", []),
        "contradictions": report.get("contradictions", []),
        "noise": report.get("noise", []),
        "suspicious": report.get("suspicious", []),
        "total_issues": sum(len(v) for v in report.values()),
    }

    return MemoryIssue3D(
        raw_items=str(items),
        axis_x=str(items),
        axis_y=axis_y,
        axis_z=axis_z,
    )


# ============================================================
# MEMORY ISSUE DETECTOR (3D‑MAX)
# ============================================================

class MemoryIssueDetector:
    """
    Detects memory issues:
        • exact duplicates
        • near-duplicates (fuzzy)
        • contradictions (semantic + structural)
        • noise entries (short, low-entropy, malformed)
        • suspicious patterns
    Now fully 3D‑MAX introspectable.
    """

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def detect(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        global _last_3d

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

        report = {
            "duplicates": duplicates,
            "near_duplicates": near_duplicates,
            "contradictions": contradictions,
            "noise": noise,
            "suspicious": suspicious,
        }

        # Attach 3D structure
        _last_3d = _build_3d(items, report)

        return report

    # ------------------------------------------------------------
    # NORMALIZATION FOR NEAR-DUPLICATE DETECTION
    # ------------------------------------------------------------
    def _normalize(self, text: str) -> str:
        t = text.lower()
        t = re.sub(r"[^a-z0-9 ]+", "", t)
        t = re.sub(r"\s+", " ", t)
        return t.strip()

    # ------------------------------------------------------------
    # CONTRADICTION DETECTION
    # ------------------------------------------------------------
    def _is_contradiction(self, text: str) -> bool:
        t = text.lower()

        if "contradiction:" in t:
            return True

        if " is " in t and " not " in t:
            return True

        if "never" in t and "i " in t:
            return True

        return False

    # ------------------------------------------------------------
    # NOISE DETECTION
    # ------------------------------------------------------------
    def _is_noise(self, text: str) -> bool:
        if len(text) < 5:
            return True

        if len(set(text)) <= 2:
            return True

        if re.fullmatch(r"[^\w]+", text):
            return True

        return False

    # ------------------------------------------------------------
    # SUSPICIOUS PATTERN DETECTION
    # ------------------------------------------------------------
    def _is_suspicious(self, text: str) -> bool:
        t = text.lower()

        if t.endswith(("...", "--", "??", "!!")):
            return True

        if "\x00" in text:
            return True

        if re.match(r"(.+)\1{2,}", t):
            return True

        return False

