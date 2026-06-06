# syntheticmind/worldmodel/world_model_manager.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from .world_graph import WorldGraph
from .world_extractor import WorldExtractor
from .world_updater import WorldUpdater
from .world_reasoner import WorldReasoner


class WorldModelManager:
    """
    High-level interface for world-model operations.

    Features:
        • structured envelopes
        • safe ingestion
        • unified querying
        • stable snapshot format
        • latency measurement
        • future-proof for simulation + reasoning layers
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.graph = WorldGraph()
        self.extractor = WorldExtractor()
        self.updater = WorldUpdater(self.graph)
        self.reasoner = WorldReasoner(self.graph)

    # ------------------------------------------------------------
    # INGEST TEXT → ENTITIES + RELATIONS → GRAPH
    # ------------------------------------------------------------
    def ingest(self, text: str) -> Dict[str, Any]:
        start = time.time()

        try:
            extracted = self.extractor.extract(text)

            if not extracted.get("ok", True):
                raise ValueError(extracted.get("error", "extraction failed"))

            updated = self.updater.update(extracted)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "text": text,
                "extracted": extracted,
                "updated": updated,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "text": text,
                "extracted": {},
                "updated": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # QUERY RELATIONS FOR A LABEL
    # ------------------------------------------------------------
    def query(self, label: str) -> Dict[str, Any]:
        start = time.time()

        try:
            result = self.reasoner.related(label)

            if not result.get("ok", True):
                raise ValueError(result.get("error", "reasoning failed"))

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "label": label,
                "result": result,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "label": label,
                "result": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # SNAPSHOT (STRUCTURED)
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a structured snapshot compatible with:
            • WorldModelDynamics
            • SimulationManager
            • Propagator
            • MetaModelRuntime world-model intent
        """

        try:
            node_map = {
                nid: {
                    "label": node.label,
                    "properties": node.properties,
                }
                for nid, node in self.graph.nodes.items()
            }

            edge_list = [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    "relation": e.relation,
                }
                for e in self.graph.edges
            ]

            return {
                "ok": True,
                "nodes": node_map,
                "edges": edge_list,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "nodes": {},
                "edges": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # UPDATE PROPERTY (USED BY SIMULATOR)
    # ------------------------------------------------------------
    def update_property(self, node_id: str, prop: str, value: Any) -> Dict[str, Any]:
        """
        Update a node's property safely.
        """

        try:
            node = self.graph.nodes.get(node_id)
            if not node:
                return {
                    "ok": False,
                    "node_id": node_id,
                    "property": prop,
                    "value": value,
                    "error": "node not found",
                }

            node.properties[prop] = value

            return {
                "ok": True,
                "node_id": node_id,
                "property": prop,
                "value": value,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "node_id": node_id,
                "property": prop,
                "value": value,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

