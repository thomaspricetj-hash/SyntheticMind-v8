from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import uuid
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class WG3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# NODE + EDGE
# ============================================================

class WorldNode:
    def __init__(self, label: str, properties: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.label = label
        self.properties = properties or {}


class WorldEdge:
    def __init__(self, source: str, target: str, relation: str):
        self.id = str(uuid.uuid4())
        self.source = source
        self.target = target
        self.relation = relation


# ============================================================
# WORLD GRAPH — MAX GRAPH + 3D‑MAX
# ============================================================

class WorldGraph:
    """
    Production-grade world graph (3D‑MAX Edition) with:
        • structured envelopes
        • duplicate-safe node creation
        • duplicate-safe edge creation
        • deterministic ordering
        • safe error handling
        • latency measurement
        • future-proof snapshot format
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.nodes: Dict[str, WorldNode] = {}
        self.edges: List[WorldEdge] = []
        self._last_3d: Optional[WG3D] = None

    # ------------------------------------------------------------
    # ADD NODE (duplicate-safe)
    # ------------------------------------------------------------
    def add_node(self, label: str, properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.time()

        try:
            # Check for existing node with same label
            for nid, node in self.nodes.items():
                if node.label == label:
                    if properties:
                        node.properties.update(properties)

                    latency = int((time.time() - start) * 1000)
                    self._last_3d = WG3D(
                        axis_x="add_node",
                        axis_y=[label, "duplicate"],
                        axis_z={"latency_ms": latency},
                    )

                    return {
                        "ok": True,
                        "latency_ms": latency,
                        "node_id": nid,
                        "label": label,
                        "properties": node.properties,
                        "duplicate": True,
                        "error": None,
                    }

            # Create new node
            node = WorldNode(label, properties)
            self.nodes[node.id] = node

            latency = int((time.time() - start) * 1000)
            self._last_3d = WG3D(
                axis_x="add_node",
                axis_y=[label, "new"],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "node_id": node.id,
                "label": label,
                "properties": node.properties,
                "duplicate": False,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WG3D(
                axis_x="add_node",
                axis_y=[label, "exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "node_id": None,
                "label": label,
                "properties": properties,
                "duplicate": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # ADD EDGE (duplicate-safe)
    # ------------------------------------------------------------
    def add_edge(self, source: str, target: str, relation: str) -> Dict[str, Any]:
        start = time.time()

        try:
            for e in self.edges:
                if e.source == source and e.target == target and e.relation == relation:
                    latency = int((time.time() - start) * 1000)
                    self._last_3d = WG3D(
                        axis_x="add_edge",
                        axis_y=[relation, "duplicate"],
                        axis_z={"latency_ms": latency},
                    )

                    return {
                        "ok": True,
                        "latency_ms": latency,
                        "edge_id": e.id,
                        "source": source,
                        "target": target,
                        "relation": relation,
                        "duplicate": True,
                        "error": None,
                    }

            edge = WorldEdge(source, target, relation)
            self.edges.append(edge)

            latency = int((time.time() - start) * 1000)
            self._last_3d = WG3D(
                axis_x="add_edge",
                axis_y=[relation, "new"],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "edge_id": edge.id,
                "source": source,
                "target": target,
                "relation": relation,
                "duplicate": False,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WG3D(
                axis_x="add_edge",
                axis_y=[relation, "exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "edge_id": None,
                "source": source,
                "target": target,
                "relation": relation,
                "duplicate": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # FIND BY LABEL
    # ------------------------------------------------------------
    def find_by_label(self, label: str) -> Dict[str, Any]:
        start = time.time()

        try:
            matches = [nid for nid, node in self.nodes.items() if node.label == label]

            latency = int((time.time() - start) * 1000)
            self._last_3d = WG3D(
                axis_x="find_by_label",
                axis_y=[label, f"count:{len(matches)}"],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "label": label,
                "node_ids": matches,
                "count": len(matches),
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WG3D(
                axis_x="find_by_label",
                axis_y=[label, "exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "label": label,
                "node_ids": [],
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # SNAPSHOT (deterministic)
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        start = time.time()

        try:
            node_map = {
                nid: {
                    "label": node.label,
                    "properties": node.properties,
                }
                for nid, node in sorted(self.nodes.items(), key=lambda x: x[0])
            }

            edge_list = [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                }
                for e in sorted(self.edges, key=lambda x: x.id)
            ]

            latency = int((time.time() - start) * 1000)
            self._last_3d = WG3D(
                axis_x="snapshot",
                axis_y=[f"nodes:{len(node_map)}", f"edges:{len(edge_list)}"],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "nodes": node_map,
                "edges": edge_list,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = WG3D(
                axis_x="snapshot",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "nodes": {},
                "edges": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }



