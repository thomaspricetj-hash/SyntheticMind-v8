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
class WUpd3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD UPDATER — MAX INGESTION + 3D‑MAX
# ============================================================

class WorldUpdater:
    """
    Applies extracted entities/relations to the world graph (3D‑MAX Edition).

    Features:
        • structured envelopes
        • duplicate-aware node creation
        • safe relation insertion
        • latency measurement
        • future-proof for LLM-based extraction
        • 3D‑MAX telemetry
    """

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self._last_3d: Optional[WUpd3D] = None

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
                    node_id = lookup["node_ids"][0]
                    entity_ids[label] = node_id
                else:
                    result = self.graph.add_node(label)
                    if result.get("ok"):
                        node_id = result["node_id"]
                        entity_ids[label] = node_id
                        added_nodes.append(result)
                    else:
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
                        "reason": "missing entity",
                    })
                    continue

                result = self.graph.add_edge(src, tgt, rel)

                if result.get("ok"):
                    added_edges.append(result)
                else:
                    skipped_edges.append({
                        "relation": (a, rel, b),
                        "reason": result.get("error", "edge creation failed"),
                    })

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = WUpd3D(
                axis_x="update",
                axis_y=[
                    f"entities:{len(entity_ids)}",
                    f"added_nodes:{len(added_nodes)}",
                    f"added_edges:{len(added_edges)}",
                    f"skipped_edges:{len(skipped_edges)}",
                ],
                axis_z={"latency_ms": latency},
            )

            # ----------------------------------------------------
            # STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": latency,
                "entities": entity_ids,
                "added_nodes": added_nodes,
                "added_edges": added_edges,
                "skipped_edges": skipped_edges,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WUpd3D(
                axis_x="update",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "entities": {},
                "added_nodes": [],
                "added_edges": [],
                "skipped_edges": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


