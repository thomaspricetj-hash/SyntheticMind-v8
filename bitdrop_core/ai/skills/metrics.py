# syntheticmind/skills/skill_metrics_store.py

from __future__ import annotations
from typing import Dict, Any
import time
from collections import defaultdict
import traceback


class SkillMetricsStore:
    """
    Tracks per-skill performance metrics.
    Provides:
        • structured envelopes
        • latency statistics (min/max/avg)
        • failure tracking
        • health scoring
        • safe snapshot
        • future-proof analytics hooks
    """

    def __init__(self):
        # skill_name -> metrics
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(self._new_metric)

    # ------------------------------------------------------------
    # INTERNAL: METRIC TEMPLATE
    # ------------------------------------------------------------
    def _new_metric(self) -> Dict[str, Any]:
        return {
            "calls": 0,
            "failures": 0,
            "total_latency_ms": 0,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "last_error": None,
            "last_updated": 0,
        }

    # ------------------------------------------------------------
    # RECORD METRIC
    # ------------------------------------------------------------
    def record(self, skill_name: str, latency_ms: int, error: str = None):
        m = self.metrics[skill_name]

        m["calls"] += 1
        m["total_latency_ms"] += latency_ms
        m["last_updated"] = time.time()
        m["last_error"] = error

        # Track failures
        if error:
            m["failures"] += 1

        # Track min/max latency
        if m["min_latency_ms"] is None or latency_ms < m["min_latency_ms"]:
            m["min_latency_ms"] = latency_ms

        if m["max_latency_ms"] is None or latency_ms > m["max_latency_ms"]:
            m["max_latency_ms"] = latency_ms

    # ------------------------------------------------------------
    # HEALTH SCORE
    # ------------------------------------------------------------
    def _health(self, m: Dict[str, Any]) -> float:
        """
        Composite health score:
            • lower latency → better
            • lower failure rate → better
        """

        if m["calls"] == 0:
            return 1.0

        avg_latency = m["total_latency_ms"] / m["calls"]
        failure_rate = m["failures"] / m["calls"]

        # Normalize latency (assume 2000ms is "bad")
        latency_penalty = min(1.0, avg_latency / 2000)

        # Failure penalty weighted more heavily
        failure_penalty = min(1.0, failure_rate * 2)

        return max(0.0, 1.0 - latency_penalty - failure_penalty)

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        out = {}

        for skill, m in self.metrics.items():
            calls = m["calls"]
            avg_latency = (m["total_latency_ms"] / calls) if calls else 0.0
            failure_rate = (m["failures"] / calls) if calls else 0.0

            out[skill] = {
                "calls": calls,
                "failures": m["failures"],
                "failure_rate": failure_rate,
                "avg_latency_ms": avg_latency,
                "min_latency_ms": m["min_latency_ms"],
                "max_latency_ms": m["max_latency_ms"],
                "last_error": m["last_error"],
                "last_updated": m["last_updated"],
                "health": self._health(m),
            }

        return out

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def safe_snapshot(self) -> Dict[str, Any]:
        try:
            return {
                "ok": True,
                "metrics": self.snapshot(),
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "metrics": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

