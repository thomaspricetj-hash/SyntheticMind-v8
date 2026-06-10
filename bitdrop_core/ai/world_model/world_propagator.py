from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Set, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WMProp3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# WORLD MODEL PROPAGATOR — MAX PROPAGATION + 3D‑MAX
# ============================================================

class WorldModelPropagator:
    """
    Propagates effects through relations in the world model (3D‑MAX Edition).

    Features:
        • multi-hop propagation
        • cycle protection
        • relation-type filtering
        • structured envelopes
        • latency measurement
        • future-proof for simulation layers
        • 3D‑MAX telemetry
    """

    def __init__(self, manager: "WorldModelManager"):
        self.manager = manager
        self._last_3d: Optional[WMProp3D] = None

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
                "depth_used": int,
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

                    # Query world model
                    q = self.manager.query(entity)
                    if not q.get("ok", True):
                        raise ValueError(q.get("error", "query failed"))

                    # Extract relations from envelope
                    rels = q.get("result", {}).get("relations", [])
                    all_relations.extend(rels)

                    # Collect next-hop targets
                    for rel in rels:
                        target = rel.get("target")
                        if target and target not in visited:
                            next_frontier.append(target)

                frontier = next_frontier

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = WMProp3D(
                axis_x="propagate",
                axis_y=[
                    f"root:{root_entity}",
                    f"visited:{len(visited)}",
                    f"relations:{len(all_relations)}",
                ],
                axis_z={
                    "latency_ms": latency,
                    "depth_used": max_depth,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "root": root_entity,
                "visited": list(visited),
                "relations": all_relations,
                "depth_used": max_depth,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WMProp3D(
                axis_x="propagate",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "root": root_entity,
                "visited": [],
                "relations": [],
                "depth_used": max_depth,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

