# syntheticmind/worldmodel/world_model_propagator.py

from __future__ import annotations
from typing import Dict, Any, List, Set
import time
import traceback


class WorldModelPropagator:
    """
    Propagates effects through relations in the world model.

    Features:
        • multi-hop propagation
        • cycle protection
        • relation-type filtering
        • structured envelopes
        • latency measurement
        • future-proof for simulation layers
    """

    def __init__(self, manager: "WorldModelManager"):
        self.manager = manager

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def propagate(self, root_entity: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Multi-hop propagation:
            root → neighbors → neighbors-of-neighbors (up to depth)

        Returns:
            {
                "ok": bool,
                "latency_ms": int,
                "root": str,
                "visited": [...],
                "relations": [...],
                "error": None
            }
        """

        start = time.time()

        try:
            visited: Set[str] = set()
            all_relations: List[Dict[str, Any]] = []

            frontier = [root_entity]

            for depth in range(max_depth):
                next_frontier = []

                for entity in frontier:
                    if entity in visited:
                        continue

                    visited.add(entity)

                    # Query world model for outgoing relations
                    rels = self.manager.query(entity)
                    all_relations.extend(rels)

                    # Collect next-hop targets
                    for rel in rels:
                        target = rel.get("target")
                        if target and target not in visited:
                            next_frontier.append(target)

                frontier = next_frontier

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "root": root_entity,
                "visited": list(visited),
                "relations": all_relations,
                "depth_used": max_depth,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "root": root_entity,
                "visited": [],
                "relations": [],
                "depth_used": max_depth,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

