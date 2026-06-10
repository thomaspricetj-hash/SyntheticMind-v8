# syntheticmind/skills/skill_metrics_store.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
from collections import defaultdict
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class SkillMetrics3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# METRICS STORE — MAX SPEED + 3D‑MAX
# ============================================================

class SkillMetricsStore:
    """
    Tracks per-skill performance metrics (3D‑MAX Edition).
    Provides:
        • structured envelopes
        • latency statistics (min/max/avg)
        • failure tracking
        • health scoring
        • safe snapshot
        • future-proof analytics hooks
        • 3D‑MAX introspection for every update/snapshot
    """

    def __init__(self):
        # skill_name -> metrics
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(self._new_metric)
        self._last_3d: Optional[SkillMetrics3D] = None

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
            "last_updated": 0.0,
        }

    # ------------------------------------------------------------
    # RECORD METRIC
    # ------------------------------------------------------------
    def record(self, skill_name: str, latency_ms: int, error: str | None = None) -> None:
        m = self.metrics[skill_name]

        m["calls"] += 1
        m["total_latency_ms"] += latency_ms
        m["last_updated"] = time.time()
        m["last_error"] = error

        if error:
            m["failures"] += 1

        if m["min_latency_ms"] is None or latency_ms < m["min_latency_ms"]:
            m["min_latency_ms"] = latency_ms

        if m["max_latency_ms"] is None or latency_ms > m["max_latency_ms"]:
            m["max_latency_ms"] = latency_ms

        calls = m["calls"]
        avg_latency = (m["total_latency_ms"] / calls) if calls else 0.0
        failure_rate = (m["failures"] / calls) if calls else 0.0
        health = self._health(m)

        self._last_3d = SkillMetrics3D(
            axis_x="record",
            axis_y=[f"skill:{skill_name}"],
            axis_z={
                "latency_ms": latency_ms,
                "calls": calls,
                "failures": m["failures"],
                "avg_latency_ms": avg_latency,
                "failure_rate": failure_rate,
                "health": health,
                "had_error": bool(error),
            },
        )

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

        latency_penalty = min(1.0, avg_latency / 2000)
        failure_penalty = min(1.0, failure_rate * 2)

        return max(0.0, 1.0 - latency_penalty - failure_penalty)

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}

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

        self._last_3d = SkillMetrics3D(
            axis_x="snapshot",
            axis_y=[f"skills:{len(out)}"],
            axis_z={
                "total_calls": sum(m["calls"] for m in self.metrics.values()),
                "total_failures": sum(m["failures"] for m in self.metrics.values()),
            },
        )

        return out

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def safe_snapshot(self) -> Dict[str, Any]:
        try:
            metrics = self.snapshot()
            return {
                "ok": True,
                "metrics": metrics,
                "error": None,
            }
        except Exception as e:
            self._last_3d = SkillMetrics3D(
                axis_x="safe_snapshot",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return {
                "ok": False,
                "metrics": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

