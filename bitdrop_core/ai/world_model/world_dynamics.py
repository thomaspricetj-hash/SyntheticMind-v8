# syntheticmind/worldmodel/world_model_dynamics.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WMDyn3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD MODEL DYNAMICS — MAX CAUSALITY + 3D‑MAX
# ============================================================

class WorldModelDynamics:
    """
    Computes causal updates, stability metrics, and structural deltas
    for the world model state (3D‑MAX Edition).

    Input state format (expected):
        {
            "nodes": [...],
            "edges": [...],
            "attributes": {...},
            "previous": {...}   # optional
        }

    Output:
        • structured envelope
        • causal metrics
        • deltas
        • stability score
        • anomaly detection
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self._last_3d: Optional[WMDyn3D] = None

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

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = WMDyn3D(
                axis_x="evaluate",
                axis_y=[
                    f"nodes:{node_count}",
                    f"edges:{edge_count}",
                    f"density:{density:.3f}",
                ],
                axis_z={
                    "latency_ms": latency,
                    "stability": stability,
                    "anomalies": len(anomalies),
                },
            )

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": latency,
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
            latency = int((time.time() - start) * 1000)

            self._last_3d = WMDyn3D(
                axis_x="evaluate",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
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

        added_nodes = list(curr_nodes - prev_nodes)
        removed_nodes = list(prev_nodes - curr_nodes)
        added_edges = list(curr_edges - prev_edges)
        removed_edges = list(prev_edges - curr_edges)

        # 3D‑MAX telemetry for delta computation
        self._last_3d = WMDyn3D(
            axis_x="_compute_deltas",
            axis_y=[
                f"added_nodes:{len(added_nodes)}",
                f"removed_nodes:{len(removed_nodes)}",
                f"added_edges:{len(added_edges)}",
                f"removed_edges:{len(removed_edges)}",
            ],
            axis_z={"ok": True},
        )

        return {
            "added_nodes": added_nodes,
            "removed_nodes": removed_nodes,
            "added_edges": added_edges,
            "removed_edges": removed_edges,
        }


