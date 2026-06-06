# syntheticmind/worldmodel/world_model_dynamics.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class WorldModelDynamics:
    """
    Computes causal updates, stability metrics, and structural deltas
    for the world model state.

    Input state format (expected):
        {
            "nodes": [...],
            "edges": [...],
            "attributes": {...}
        }

    Output:
        • structured envelope
        • causal metrics
        • deltas
        • stability score
        • anomaly detection
    """

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def evaluate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()

        try:
            nodes = state.get("nodes", [])
            edges = state.get("edges", [])

            node_count = len(nodes)
            edge_count = len(edges)

            # ----------------------------------------------------
            # BASIC METRICS
            # ----------------------------------------------------
            complexity = node_count + edge_count
            density = edge_count / max(1, node_count)

            # ----------------------------------------------------
            # CAUSAL HEURISTICS (lightweight)
            # ----------------------------------------------------
            # More edges → more coupling → lower stability
            stability = max(0.0, 1.0 - (density * 0.1))

            # ----------------------------------------------------
            # DELTA DETECTION
            # ----------------------------------------------------
            deltas = self._compute_deltas(state)

            # ----------------------------------------------------
            # ANOMALY DETECTION
            # ----------------------------------------------------
            anomalies = []
            if density > 5:
                anomalies.append("graph-too-dense")
            if node_count == 0:
                anomalies.append("empty-world")

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "metrics": {
                    "nodes": node_count,
                    "edges": edge_count,
                    "complexity": complexity,
                    "density": density,
                    "stability": stability,
                },
                "deltas": deltas,
                "anomalies": anomalies,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "metrics": {},
                "deltas": {},
                "anomalies": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL: COMPUTE DELTAS
    # ------------------------------------------------------------
    def _compute_deltas(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detects structural changes between:
            • current state
            • previous snapshot (if provided)
        """

        prev = state.get("previous", {})
        prev_nodes = set(prev.get("nodes", []))
        prev_edges = set(prev.get("edges", []))

        curr_nodes = set(state.get("nodes", []))
        curr_edges = set(state.get("edges", []))

        return {
            "added_nodes": list(curr_nodes - prev_nodes),
            "removed_nodes": list(prev_nodes - curr_nodes),
            "added_edges": list(curr_edges - prev_edges),
            "removed_edges": list(prev_edges - curr_edges),
        }

