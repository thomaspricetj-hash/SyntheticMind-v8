from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time

from .detector import MemoryIssueDetector
from .cleaner import MemoryCleaner


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class MemoryHealer3D:
    """
    3D structural view of a memory healing cycle.

    axis_x: raw issues dict (stringified)
    axis_y: structural decomposition (issue categories)
    axis_z: metadata (cleaned, skipped, latency, totals)
    """
    raw_input: str
    axis_x: str
    axis_y: list
    axis_z: Dict[str, Any]


_last_3d: Optional[MemoryHealer3D] = None


def _build_3d(issues: Dict[str, Any], cleaned: Dict[str, Any], skipped: bool, latency_ms: int) -> MemoryHealer3D:
    axis_y = list(issues.keys()) if issues else []

    axis_z = {
        "skipped": skipped,
        "latency_ms": latency_ms,
        "issues": issues,
        "cleaned": cleaned,
        "total_issues": sum(len(v) for v in issues.values()) if issues else 0,
        "total_cleaned": cleaned.get("total_actions", 0) if cleaned else 0,
    }

    return MemoryHealer3D(
        raw_input=str(issues),
        axis_x=str(issues),
        axis_y=axis_y,
        axis_z=axis_z,
    )


# ============================================================
# MEMORY HEALER (3D‑MAX)
# ============================================================

class MemoryHealer:
    """
    Full memory healing pipeline:
        • detect issues
        • clean memory
        • return structured healing report
        • track cycle metadata
    Now fully 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 200):
        self.runtime = runtime
        self.detector = MemoryIssueDetector()
        self.cleaner = MemoryCleaner(runtime)
        self.window = window
        self.last_ts = 0.0
        self._last_3d: Optional[MemoryHealer3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        start = time.time()

        # --------------------------------------------------------
        # 1. Pull memory items
        # --------------------------------------------------------
        items = self.runtime.memory.last_n(self.window)

        if not items:
            report = self._report({}, {}, True, start)
            self._last_3d = _build_3d({}, {}, True, report["latency_ms"])
            return report

        # --------------------------------------------------------
        # 2. Detect issues
        # --------------------------------------------------------
        issues = self.detector.detect(items)

        # If no issues → skip cleaning
        if not self._has_issues(issues):
            report = self._report(issues, {}, True, start)
            self._last_3d = _build_3d(issues, {}, True, report["latency_ms"])
            return report

        # --------------------------------------------------------
        # 3. Clean issues
        # --------------------------------------------------------
        cleaned = self.cleaner.clean(issues)

        # --------------------------------------------------------
        # 4. Log healing event
        # --------------------------------------------------------
        self.runtime.memory.remember(
            f"[memory-healer] cleaned {cleaned.get('total_actions', 0)} issues"
        )

        # --------------------------------------------------------
        # 5. Return structured report
        # --------------------------------------------------------
        report = self._report(issues, cleaned, False, start)
        self._last_3d = _build_3d(issues, cleaned, False, report["latency_ms"])
        return report

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _has_issues(self, issues: Dict[str, Any]) -> bool:
        return any(len(v) > 0 for v in issues.values())

    def _report(self, issues, cleaned, skipped, start):
        return {
            "issues": issues,
            "cleaned": cleaned,
            "skipped": skipped,
            "latency_ms": int((time.time() - start) * 1000),
        }

