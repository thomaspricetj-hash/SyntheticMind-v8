# syntheticmind/worldmodel/world_updater.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback

from .world_graph import WorldGraph


class WorldUpdater:
    """
    Applies extracted entities/relations to the world graph.

    Features:
        • structured envelopes
        • duplicate-aware node creation
        • safe relation insertion
        • latency measurement
        • future-proof for LLM-based extraction
    """

    def __init__(self, graph: WorldGraph):
        self.graph = graph

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def update(self, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """
        extracted = {
            "entities": [...],
            "relations": [(a, rel, b), ...]
        }
        """

        start = time.time()

        try:
            entity_ids: Dict[str, str] = {}
            added_nodes: List[Dict[str, Any]] = []
            added_edges: List[Dict[str, Any]] = []
            skipped_edges: List[Dict[str, Any]] = []

            # ----------------------------------------------------
            # ADD ENTITIES (duplicate-aware)
            # ----------------------------------------------------
            for label in extracted.get("entities", []):
                lookup = self.graph.find_by_label(label)

                if lookup.get("ok") and lookup.get("count", 0) > 0:
                    # Reuse existing node
                    node_id = lookup["node_ids"][0]
                    entity_ids[label] = node_id
                else:
                    # Create new node
                    result = self.graph.add_node(label)
                    if result.get("ok"):
                        node_id = result["node_id"]
                        entity_ids[label] = node_id
                        added_nodes.append(result)
                    else:
                        # Node creation failed
                        entity_ids[label] = None

            # ----------------------------------------------------
            # ADD RELATIONS
            # ----------------------------------------------------
            for a, rel, b in extracted.get("relations", []):
                src = entity_ids.get(a)
                tgt = entity_ids.get(b)

                if not src or not tgt:
                    skipped_edges.append({
                        "relation": (a, rel, b),
                        "reason": "missing entity"
                    })
                    continue

                result = self.graph.add_edge(src, tgt, rel)

                if result.get("ok"):
                    added_edges.append(result)
                else:
                    skipped_edges.append({
                        "relation": (a, rel, b),
                        "reason": result.get("error", "edge creation failed")
                    })

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "entities": entity_ids,
                "added_nodes": added_nodes,
                "added_edges": added_edges,
                "skipped_edges": skipped_edges,
                "error": None,
            }

        except Exception as e:
            # ----------------------------------------------------
            # FAILURE ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "entities": {},
                "added_nodes": [],
                "added_edges": [],
                "skipped_edges": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

