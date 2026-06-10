from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from .world_graph import WorldGraph


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WReason3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD REASONER — MAX REASONING + 3D‑MAX
# ============================================================

class WorldReasoner:
    """
    Performs reasoning over the world graph (3D‑MAX Edition).

    Features:
        • structured envelopes
        • multi-node reasoning
        • relation-type filtering
        • latency measurement
        • safe error handling
        • future-proof for causal inference
        • 3D‑MAX telemetry
    """

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self._last_3d: Optional[WReason3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def related(self, label: str, relation_filter: str | None = None) -> Dict[str, Any]:
        """
        Returns all relations involving nodes with the given label.

        Output:
            {
                "ok": bool,
                "latency_ms": int,
                "label": str,
                "node_ids": [...],
                "relations": [...],
                "relation_filter": str | None,
                "count": int,
                "error": None
            }
        """

        start = time.time()

        try:
            # Lookup nodes by label
            lookup = self.graph.find_by_label(label)
            if not lookup.get("ok"):
                raise ValueError(lookup.get("error", "label lookup failed"))

            node_ids = lookup.get("node_ids", [])

            results: List[Dict[str, Any]] = []

            # Iterate over edges
            for edge in self.graph.edges:
                # Optional relation filter
                if relation_filter and edge.relation != relation_filter:
                    continue

                # Outgoing
                if edge.source in node_ids:
                    target_label = self.graph.nodes[edge.target].label
                    results.append({
                        "source_label": label,
                        "relation": edge.relation,
                        "target_label": target_label,
                        "direction": "outgoing",
                        "edge_id": edge.id,
                    })

                # Incoming
                if edge.target in node_ids:
                    source_label = self.graph.nodes[edge.source].label
                    results.append({
                        "source_label": source_label,
                        "relation": edge.relation,
                        "target_label": label,
                        "direction": "incoming",
                        "edge_id": edge.id,
                    })

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = WReason3D(
                axis_x="related",
                axis_y=[
                    f"label:{label}",
                    f"nodes:{len(node_ids)}",
                    f"relations:{len(results)}",
                ],
                axis_z={
                    "latency_ms": latency,
                    "filter": relation_filter,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "label": label,
                "node_ids": node_ids,
                "relations": results,
                "relation_filter": relation_filter,
                "count": len(results),
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WReason3D(
                axis_x="related",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "label": label,
                "node_ids": [],
                "relations": [],
                "relation_filter": relation_filter,
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

