# syntheticmind/taskgraph/task_graph.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from .node import TaskNode


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class TaskGraph3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TASK GRAPH — MAX STRUCT + 3D‑MAX
# ============================================================

class TaskGraph:
    """
    Directed acyclic graph of tasks (3D‑MAX Edition).
    Provides:
        • structured graph metadata
        • cycle detection
        • safe node linking
        • ready-node resolution
        • graph introspection
        • 3D‑MAX telemetry
        • future-proof hooks for branching + parallelism
    """

    def __init__(self, goal: str):
        self.goal = goal
        self.nodes: Dict[str, TaskNode] = {}
        self.entry_nodes: List[str] = []
        self.exit_nodes: List[str] = []
        self.created_at = time.time()
        self._last_3d: Optional[TaskGraph3D] = None

    # ------------------------------------------------------------
    # ADD NODE
    # ------------------------------------------------------------
    def add_node(self, node: TaskNode, is_entry: bool = False, is_exit: bool = False):
        self.nodes[node.id] = node

        if is_entry:
            self.entry_nodes.append(node.id)

        if is_exit:
            self.exit_nodes.append(node.id)

        self._last_3d = TaskGraph3D(
            axis_x="add_node",
            axis_y=[f"node:{node.id}", f"type:{node.type}"],
            axis_z={
                "is_entry": is_entry,
                "is_exit": is_exit,
                "node_count": len(self.nodes),
            },
        )

    # ------------------------------------------------------------
    # LINK NODES
    # ------------------------------------------------------------
    def link(self, parent_id: str, child_id: str):
        if parent_id not in self.nodes:
            raise ValueError(f"unknown parent node: {parent_id}")
        if child_id not in self.nodes:
            raise ValueError(f"unknown child node: {child_id}")

        parent = self.nodes[parent_id]
        child = self.nodes[child_id]

        parent.add_child(child_id)
        child.add_parent(parent_id)

        self._last_3d = TaskGraph3D(
            axis_x="link",
            axis_y=[f"{parent_id}->{child_id}"],
            axis_z={"node_count": len(self.nodes)},
        )

    # ------------------------------------------------------------
    # READY NODES
    # ------------------------------------------------------------
    def get_ready_nodes(self) -> List[TaskNode]:
        """
        Nodes whose parents are all done and which are still pending.
        """
        ready: List[TaskNode] = []
        for node in self.nodes.values():
            if node.status == "pending":
                if all(self.nodes[p].status == "done" for p in node.parents):
                    ready.append(node)

        self._last_3d = TaskGraph3D(
            axis_x="get_ready_nodes",
            axis_y=[f"ready:{len(ready)}"],
            axis_z={"node_count": len(self.nodes)},
        )

        return ready

    # ------------------------------------------------------------
    # COMPLETION CHECK
    # ------------------------------------------------------------
    def is_complete(self) -> bool:
        complete = all(n.status in ("done", "error") for n in self.nodes.values())

        self._last_3d = TaskGraph3D(
            axis_x="is_complete",
            axis_y=[f"complete:{complete}"],
            axis_z={"node_count": len(self.nodes)},
        )

        return complete

    # ------------------------------------------------------------
    # CYCLE DETECTION (safety)
    # ------------------------------------------------------------
    def has_cycle(self) -> bool:
        """
        Detect cycles using DFS.
        """
        visited = set()
        stack = set()

        def dfs(nid: str) -> bool:
            if nid in stack:
                return True
            if nid in visited:
                return False

            visited.add(nid)
            stack.add(nid)

            for c in self.nodes[nid].children:
                if dfs(c):
                    return True

            stack.remove(nid)
            return False

        has_cycle = any(dfs(nid) for nid in self.nodes)

        self._last_3d = TaskGraph3D(
            axis_x="has_cycle",
            axis_y=[f"cycle:{has_cycle}"],
            axis_z={"node_count": len(self.nodes)},
        )

        return has_cycle

    # ------------------------------------------------------------
    # GRAPH SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of the graph.
        """
        try:
            snap = {
                "ok": True,
                "goal": self.goal,
                "created_at": self.created_at,
                "node_count": len(self.nodes),
                "entry_nodes": self.entry_nodes,
                "exit_nodes": self.exit_nodes,
                "nodes": {
                    nid: {
                        "type": n.type,
                        "status": n.status,
                        "parents": n.parents,
                        "children": n.children,
                        "result": n.result,
                        "error": n.error,
                        "latency_ms": getattr(n, "latency_ms", None),
                    }
                    for nid, n in self.nodes.items()
                },
                "has_cycle": self.has_cycle(),
                "error": None,
            }

            self._last_3d = TaskGraph3D(
                axis_x="snapshot",
                axis_y=[f"nodes:{len(self.nodes)}"],
                axis_z={"has_cycle": snap["has_cycle"]},
            )

            return snap

        except Exception as e:
            self._last_3d = TaskGraph3D(
                axis_x="snapshot",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )
            return {
                "ok": False,
                "goal": self.goal,
                "node_count": len(self.nodes),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

