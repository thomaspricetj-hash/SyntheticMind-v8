from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import statistics


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class MetaOpt3D:
    """
    3D structural view of a meta-optimization cycle.

    axis_x: high-level operation ("record_call", "suggest")
    axis_y: structural decomposition (intents, anomaly labels)
    axis_z: metadata (window, counts, stats, suggestions)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# META OPTIMIZER (3D‑MAX)
# ============================================================

class MetaOptimizer:
    """
    Observes runtime behavior and suggests/tunes architectural parameters:
        • routing intents
        • refinement passes
        • model choices
        • taskgraph usage
        • anomaly detection
        • drift detection
        • rolling-window latency analysis
    Now 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 200):
        self.runtime = runtime
        self.window = window
        self.history: List[Dict[str, Any]] = []
        self._last_3d: Optional[MetaOpt3D] = None

    # ------------------------------------------------------------
    # RECORDING
    # ------------------------------------------------------------
    def record_call(self, intent: str, latency_ms: int, meta: Dict[str, Any]):
        """Record a runtime call with timestamp + metadata."""
        entry = {
            "t": time.time(),
            "intent": intent,
            "latency_ms": latency_ms,
            "meta": meta,
        }
        self.history.append(entry)

        # Trim to rolling window
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]

        # 3D snapshot for recording
        self._last_3d = MetaOpt3D(
            axis_x="record_call",
            axis_y=[intent],
            axis_z={
                "window": self.window,
                "history_len": len(self.history),
                "last_latency_ms": latency_ms,
                "meta_keys": list(meta.keys()),
            },
        )

    # ------------------------------------------------------------
    # SUGGESTIONS
    # ------------------------------------------------------------
    def suggest(self) -> Dict[str, Any]:
        """
        Produce a structured optimization report:
            • per-intent stats
            • latency anomalies
            • routing imbalance
            • refinement tuning
            • taskgraph encouragement
        """

        if not self.history:
            out = {"suggestions": {}, "stats": {}, "anomalies": []}
            self._last_3d = MetaOpt3D(
                axis_x="suggest",
                axis_y=[],
                axis_z={
                    "window": self.window,
                    "history_len": 0,
                    "empty": True,
                },
            )
            return out

        stats = self._compute_stats()
        anomalies = self._detect_anomalies(stats)
        suggestions = self._generate_suggestions(stats, anomalies)

        # 3D snapshot for suggestion cycle
        self._last_3d = MetaOpt3D(
            axis_x="suggest",
            axis_y=list(stats.keys()),
            axis_z={
                "window": self.window,
                "history_len": len(self.history),
                "intent_count": len(stats),
                "anomaly_count": len(anomalies),
                "has_suggestions": bool(suggestions),
            },
        )

        return {
            "stats": stats,
            "anomalies": anomalies,
            "suggestions": suggestions,
        }

    # ------------------------------------------------------------
    # INTERNAL: STATISTICS
    # ------------------------------------------------------------
    def _compute_stats(self) -> Dict[str, Any]:
        """Compute per-intent statistics over the rolling window."""

        by_intent: Dict[str, Dict[str, Any]] = {}

        for h in self.history:
            intent = h["intent"]
            by_intent.setdefault(intent, {"latencies": [], "calls": 0})
            by_intent[intent]["latencies"].append(h["latency_ms"])
            by_intent[intent]["calls"] += 1

        stats: Dict[str, Any] = {}
        for intent, d in by_intent.items():
            lat = d["latencies"]
            stats[intent] = {
                "calls": d["calls"],
                "avg_latency": statistics.mean(lat),
                "p95_latency": (
                    statistics.quantiles(lat, n=20)[-1] if len(lat) > 5 else max(lat)
                ),
                "max_latency": max(lat),
            }

        return stats

    # ------------------------------------------------------------
    # INTERNAL: ANOMALY DETECTION
    # ------------------------------------------------------------
    def _detect_anomalies(self, stats: Dict[str, Any]) -> List[str]:
        """Detect intents with unusually high latency or low usage."""

        anomalies: List[str] = []

        for intent, s in stats.items():
            avg = s["avg_latency"]
            p95 = s["p95_latency"]

            if p95 > 2000:
                anomalies.append(f"{intent}: high latency (p95={p95}ms)")

            if s["calls"] <= 1:
                anomalies.append(f"{intent}: underused (calls={s['calls']})")

        return anomalies

    # ------------------------------------------------------------
    # INTERNAL: SUGGESTION ENGINE
    # ------------------------------------------------------------
    def _generate_suggestions(self, stats: Dict[str, Any], anomalies: List[str]) -> Dict[str, Any]:
        """Generate actionable architectural suggestions."""

        suggestions: Dict[str, Any] = {}

        # SELF-REFINE TUNING
        sr = stats.get("self_refine")
        if sr:
            if sr["avg_latency"] > 1500:
                suggestions["self_refine_passes"] = 1
            elif sr["avg_latency"] < 800:
                suggestions["self_refine_passes"] = 3
            else:
                suggestions["self_refine_passes"] = 2

        # TASKGRAPH ENCOURAGEMENT
        tg = stats.get("taskgraph")
        if tg and tg["calls"] < 3:
            suggestions["encourage_taskgraph"] = True

        # ROUTING IMBALANCE
        if len(stats) > 1:
            max_intent = max(stats, key=lambda k: stats[k]["calls"])
            min_intent = min(stats, key=lambda k: stats[k]["calls"])

            if stats[max_intent]["calls"] > 5 * stats[min_intent]["calls"]:
                suggestions["routing_rebalance"] = {
                    "overused": max_intent,
                    "underused": min_intent,
                }

        # ANOMALY-BASED SUGGESTIONS
        if anomalies:
            suggestions["review_anomalies"] = anomalies

        return suggestions


