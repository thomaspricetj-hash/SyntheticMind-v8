from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class MemoryCleaner3D:
    """
    3D structural view of a memory-cleaning operation.

    axis_x: raw issues dict
    axis_y: structural decomposition (issue categories)
    axis_z: metadata (removed, flagged, quarantined, totals)
    """
    raw_input: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[MemoryCleaner3D] = None


def _build_3d(issues: Dict[str, Any], report: Dict[str, Any]) -> MemoryCleaner3D:
    axis_y = list(issues.keys())

    axis_z = {
        "removed": report.get("removed", []),
        "flagged": report.get("flagged", []),
        "quarantined": report.get("quarantined", []),
        "total_actions": report.get("total_actions", 0),
    }

    return MemoryCleaner3D(
        raw_input=str(issues),
        axis_x=str(issues),
        axis_y=axis_y,
        axis_z=axis_z,
    )


# ============================================================
# MEMORY CLEANER (3D‑MAX)
# ============================================================

class MemoryCleaner:
    """
    Applies healing operations to memory:
        • deduplication
        • contradiction flagging
        • noise removal
        • quarantine of suspicious items
        • structured cleanup reporting
    Now fully 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self._last_3d: Optional[MemoryCleaner3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def clean(self, issues: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a cleanup cycle.
        Returns a structured report describing what was changed.
        """

        removed = []
        flagged = []
        quarantined = []

        # --------------------------------------------------------
        # 1. Remove duplicates
        # --------------------------------------------------------
        for item in issues.get("duplicates", []):
            if self._safe_remove(item):
                removed.append(item)

        # --------------------------------------------------------
        # 2. Flag contradictions
        # --------------------------------------------------------
        for c in issues.get("contradictions", []):
            self.runtime.memory.remember(f"[flagged-contradiction] {c}")
            flagged.append(c)

        # --------------------------------------------------------
        # 3. Remove noise
        # --------------------------------------------------------
        for n in issues.get("noise", []):
            if self._safe_remove(n):
                removed.append(n)

        # --------------------------------------------------------
        # 4. Quarantine suspicious items
        # --------------------------------------------------------
        for q in issues.get("suspicious", []):
            self.runtime.memory.remember(f"[quarantine] {q}")
            quarantined.append(q)

        # --------------------------------------------------------
        # 5. Structured cleanup report
        # --------------------------------------------------------
        report = {
            "removed": removed,
            "flagged": flagged,
            "quarantined": quarantined,
            "total_actions": len(removed) + len(flagged) + len(quarantined),
        }

        # Attach 3D structure
        self._last_3d = _build_3d(issues, report)

        return report

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _safe_remove(self, item: Any) -> bool:
        """
        Remove an item only if:
            • it exists
            • it is not a high‑value fact
            • it is not a skill
            • it is not a preference
        """

        text = str(item).lower()

        protected_prefixes = (
            "[fact]",
            "[skill]",
            "[preference]",
            "[theme]",
            "[trend]",
        )

        if any(text.startswith(p) for p in protected_prefixes):
            return False

        try:
            self.runtime.memory.remove(item)
            return True
        except Exception:
            return False

