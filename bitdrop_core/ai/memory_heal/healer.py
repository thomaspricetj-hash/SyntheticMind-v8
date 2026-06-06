# ai/memory/memory_healer.py

from __future__ import annotations
from typing import Dict, Any
import time

from .detector import MemoryIssueDetector
from .cleaner import MemoryCleaner


class MemoryHealer:
    """
    Full memory healing pipeline:
        • detect issues
        • clean memory
        • return structured healing report
        • track cycle metadata
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 200):
        self.runtime = runtime
        self.detector = MemoryIssueDetector()
        self.cleaner = MemoryCleaner(runtime)
        self.window = window

        # Track last healing timestamp to avoid over‑healing
        self.last_ts = 0.0

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """
        Perform one healing cycle:
            • pull memory
            • detect issues
            • clean issues
            • return structured report
        """

        start = time.time()

        # --------------------------------------------------------
        # 1. Pull memory items
        # --------------------------------------------------------
        items = self.runtime.memory.last_n(self.window)

        if not items:
            return self._report(
                issues={},
                cleaned={},
                skipped=True,
                start=start,
            )

        # --------------------------------------------------------
        # 2. Detect issues
        # --------------------------------------------------------
        issues = self.detector.detect(items)

        # If no issues → skip cleaning
        if not self._has_issues(issues):
            return self._report(
                issues=issues,
                cleaned={},
                skipped=True,
                start=start,
            )

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
        return self._report(
            issues=issues,
            cleaned=cleaned,
            skipped=False,
            start=start,
        )

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _has_issues(self, issues: Dict[str, Any]) -> bool:
        """Check if any issue category contains items."""
        return any(len(v) > 0 for v in issues.values())

    def _report(self, issues, cleaned, skipped, start):
        """Build a structured healing report."""
        return {
            "issues": issues,
            "cleaned": cleaned,
            "skipped": skipped,
            "latency_ms": int((time.time() - start) * 1000),
        }
