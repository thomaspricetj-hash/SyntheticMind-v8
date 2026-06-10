# ai/background/learner.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from .analyzer import BackgroundAnalyzer
from .consolidator import BackgroundConsolidator


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class BackgroundLearner3D:
    """
    3D structural view of a background learning cycle.

    axis_x: high-level operation ("run")
    axis_y: structural decomposition (processed count, skipped flag)
    axis_z: metadata (latency, last_ts, analyzer_3d, consolidator_3d)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# BACKGROUND LEARNER (3D‑MAX)
# ============================================================

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
    Now fully 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 50):
        self.runtime = runtime
        self.analyzer = BackgroundAnalyzer()
        self.consolidator = BackgroundConsolidator(runtime)

        self.window = window
        self.last_ts = 0.0
        self._last_3d: Optional[BackgroundLearner3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        start = time.time()

        try:
            items = self._get_new_items()

            # No new items → skip cycle
            if not items:
                latency_ms = int((time.time() - start) * 1000)

                self._last_3d = BackgroundLearner3D(
                    axis_x="run",
                    axis_y=[f"processed:0", "skipped:True"],
                    axis_z={
                        "latency_ms": latency_ms,
                        "last_ts": self.last_ts,
                        "analyzer_3d": None,
                        "consolidator_3d": None,
                    },
                )

                return {
                    "ok": True,
                    "insights": {},
                    "processed": 0,
                    "skipped": True,
                    "latency_ms": latency_ms,
                    "last_ts": self.last_ts,
                    "error": None,
                }

            # Analyze
            insights = self.analyzer.analyze(items)
            analyzer_3d = getattr(self.analyzer, "_last_3d", None)

            # Consolidate
            self.consolidator.consolidate(insights)
            consolidator_3d = getattr(self.consolidator, "_last_3d", None)

            # Update timestamp
            self._update_last_ts(items)

            latency_ms = int((time.time() - start) * 1000)

            # 3D envelope
            self._last_3d = BackgroundLearner3D(
                axis_x="run",
                axis_y=[f"processed:{len(items)}", "skipped:False"],
                axis_z={
                    "latency_ms": latency_ms,
                    "last_ts": self.last_ts,
                    "analyzer_3d": analyzer_3d,
                    "consolidator_3d": consolidator_3d,
                },
            )

            return {
                "ok": True,
                "insights": insights,
                "processed": len(items),
                "skipped": False,
                "latency_ms": latency_ms,
                "last_ts": self.last_ts,
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)

            self._last_3d = BackgroundLearner3D(
                axis_x="run",
                axis_y=["processed:0", "skipped:True"],
                axis_z={
                    "latency_ms": latency_ms,
                    "last_ts": self.last_ts,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )

            return {
                "ok": False,
                "insights": {},
                "processed": 0,
                "skipped": True,
                "latency_ms": latency_ms,
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

