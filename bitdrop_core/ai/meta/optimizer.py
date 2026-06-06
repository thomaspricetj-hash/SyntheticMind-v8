# ai/meta/meta_optimizer.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import statistics


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
    """

    def __init__(self, runtime: "MetaModelRuntime", window: int = 200):
        self.runtime = runtime
        self.window = window
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # RECORDING
    # ------------------------------------------------------------
    def record_call(self, intent: str, latency_ms: int, meta: Dict[str, Any]):
        """Record a runtime call with timestamp + metadata."""
        self.history.append({
            "t": time.time(),
            "intent": intent,
            "latency_ms": latency_ms,
            "meta": meta,
        })

        # Trim to rolling window
        if len(self.history) > self.window:
            self.history = self.history[-self.window:]

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
            return {"suggestions": {}, "stats": {}, "anomalies": []}

        stats = self._compute_stats()
        anomalies = self._detect_anomalies(stats)
        suggestions = self._generate_suggestions(stats, anomalies)

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

        stats = {}
        for intent, d in by_intent.items():
            lat = d["latencies"]
            stats[intent] = {
                "calls": d["calls"],
                "avg_latency": statistics.mean(lat),
                "p95_latency": statistics.quantiles(lat, n=20)[-1] if len(lat) > 5 else max(lat),
                "max_latency": max(lat),
            }

        return stats

    # ------------------------------------------------------------
    # INTERNAL: ANOMALY DETECTION
    # ------------------------------------------------------------
    def _detect_anomalies(self, stats: Dict[str, Any]) -> List[str]:
        """Detect intents with unusually high latency or low usage."""

        anomalies = []

        for intent, s in stats.items():
            avg = s["avg_latency"]
            p95 = s["p95_latency"]

            # High-latency anomaly
            if p95 > 2000:
                anomalies.append(f"{intent}: high latency (p95={p95}ms)")

            # Underuse anomaly
            if s["calls"] <= 1:
                anomalies.append(f"{intent}: underused (calls={s['calls']})")

        return anomalies

    # ------------------------------------------------------------
    # INTERNAL: SUGGESTION ENGINE
    # ------------------------------------------------------------
    def _generate_suggestions(self, stats: Dict[str, Any], anomalies: List[str]) -> Dict[str, Any]:
        """Generate actionable architectural suggestions."""

        suggestions = {}

        # -----------------------------
        # SELF-REFINE TUNING
        # -----------------------------
        sr = stats.get("self_refine")
        if sr:
            if sr["avg_latency"] > 1500:
                suggestions["self_refine_passes"] = 1
            elif sr["avg_latency"] < 800:
                suggestions["self_refine_passes"] = 3
            else:
                suggestions["self_refine_passes"] = 2

        # -----------------------------
        # TASKGRAPH ENCOURAGEMENT
        # -----------------------------
        tg = stats.get("taskgraph")
        if tg and tg["calls"] < 3:
            suggestions["encourage_taskgraph"] = True

        # -----------------------------
        # ROUTING IMBALANCE
        # -----------------------------
        if len(stats) > 1:
            max_intent = max(stats, key=lambda k: stats[k]["calls"])
            min_intent = min(stats, key=lambda k: stats[k]["calls"])

            if stats[max_intent]["calls"] > 5 * stats[min_intent]["calls"]:
                suggestions["routing_rebalance"] = {
                    "overused": max_intent,
                    "underused": min_intent,
                }

        # -----------------------------
        # ANOMALY-BASED SUGGESTIONS
        # -----------------------------
        if anomalies:
            suggestions["review_anomalies"] = anomalies

        return suggestions

