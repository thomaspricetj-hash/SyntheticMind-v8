# ai/background/learner.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback

from .analyzer import BackgroundAnalyzer
from .consolidator import BackgroundConsolidator


class BackgroundLearner:
    """
    Periodically scans memory and extracts new knowledge.

    Features:
        • incremental learning (only new items)
        • deduplication
        • safety around empty memory
        • cycle metadata
        • throttled consolidation
        • structured logging
        • timestamp-aware processing
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 50):
        self.runtime = runtime
        self.analyzer = BackgroundAnalyzer()
        self.consolidator = BackgroundConsolidator(runtime)

        self.window = window
        self.last_ts = 0.0

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        start = time.time()

        try:
            items = self._get_new_items()

            if not items:
                return {
                    "ok": True,
                    "insights": {},
                    "processed": 0,
                    "skipped": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "last_ts": self.last_ts,
                    "error": None,
                }

            # Analyze
            insights = self.analyzer.analyze(items)

            # Consolidate
            self.consolidator.consolidate(insights)

            # Update timestamp
            self._update_last_ts(items)

            return {
                "ok": True,
                "insights": insights,
                "processed": len(items),
                "skipped": False,
                "latency_ms": int((time.time() - start) * 1000),
                "last_ts": self.last_ts,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "insights": {},
                "processed": 0,
                "skipped": True,
                "latency_ms": int((time.time() - start) * 1000),
                "last_ts": self.last_ts,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _get_new_items(self) -> List[Dict[str, Any]]:
        """
        Pull only memory items newer than last_ts.
        Falls back to last N items if timestamps missing.
        """

        # Timestamp-aware retrieval
        if hasattr(self.runtime.memory, "get_since"):
            items = self.runtime.memory.get_since(self.last_ts)
            if items:
                return items[-self.window:]

        # Fallback: last N items
        items = self.runtime.memory.last_n(self.window)

        # Filter by timestamp
        filtered = []
        for item in items:
            ts = item.get("ts") or item.get("timestamp")
            if ts and ts > self.last_ts:
                filtered.append(item)

        return filtered or items

    def _update_last_ts(self, items: List[Dict[str, Any]]):
        timestamps = [
            i.get("ts") or i.get("timestamp")
            for i in items
            if (i.get("ts") or i.get("timestamp"))
        ]
        if timestamps:
            self.last_ts = max(timestamps)
