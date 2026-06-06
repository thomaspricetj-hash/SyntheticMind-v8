from __future__ import annotations
from typing import Dict, List, Any, Optional
import uuid
import time
import traceback


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


class WorldGraph:
    """
    Production-grade world graph with:
        • structured envelopes
        • duplicate-safe node creation
        • duplicate-safe edge creation
        • deterministic ordering
        • safe error handling
        • latency measurement
        • future-proof snapshot format
    """

    def __init__(self):
        self.nodes: Dict[str, WorldNode] = {}
        self.edges: List[WorldEdge] = []

    # ------------------------------------------------------------
    # ADD NODE (duplicate-safe)
    # ------------------------------------------------------------
    def add_node(self, label: str, properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        start = time.time()

        try:
            # Check for existing node with same label
            for nid, node in self.nodes.items():
                if node.label == label:
                    # Merge properties if provided
                    if properties:
                        node.properties.update(properties)

                    return {
                        "ok": True,
                        "latency_ms": int((time.time() - start) * 1000),
                        "node_id": nid,
                        "label": label,
                        "properties": node.properties,
                        "duplicate": True,
                        "error": None,
                    }

            # Create new node
            node = WorldNode(label, properties)
            self.nodes[node.id] = node

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "node_id": node.id,
                "label": label,
                "properties": node.properties,
                "duplicate": False,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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
            # Check for duplicate edge
            for e in self.edges:
                if e.source == source and e.target == target and e.relation == relation:
                    return {
                        "ok": True,
                        "latency_ms": int((time.time() - start) * 1000),
                        "edge_id": e.id,
                        "source": source,
                        "target": target,
                        "relation": relation,
                        "duplicate": True,
                        "error": None,
                    }

            # Create new edge
            edge = WorldEdge(source, target, relation)
            self.edges.append(edge)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "edge_id": edge.id,
                "source": source,
                "target": target,
                "relation": relation,
                "duplicate": False,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "label": label,
                "node_ids": matches,
                "count": len(matches),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "nodes": node_map,
                "edges": edge_list,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "nodes": {},
                "edges": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


