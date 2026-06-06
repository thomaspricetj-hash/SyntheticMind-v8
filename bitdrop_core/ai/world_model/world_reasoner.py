# syntheticmind/worldmodel/world_reasoner.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback

from .world_graph import WorldGraph


class WorldReasoner:
    """
    Performs reasoning over the world graph.

    Features:
        • structured envelopes
        • multi-node reasoning
        • relation-type filtering
        • latency measurement
        • safe error handling
        • future-proof for causal inference
    """

    def __init__(self, graph: WorldGraph):
        self.graph = graph

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

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "label": label,
                "node_ids": node_ids,
                "relations": results,
                "relation_filter": relation_filter,
                "count": len(results),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "label": label,
                "node_ids": [],
                "relations": [],
                "relation_filter": relation_filter,
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
