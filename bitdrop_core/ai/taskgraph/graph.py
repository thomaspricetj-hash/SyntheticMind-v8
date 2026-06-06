# syntheticmind/taskgraph/task_graph.py

from __future__ import annotations
from typing import Dict, Any, List, Optional
import time
import traceback

from .node import TaskNode


class TaskGraph:
    """
    Directed acyclic graph of tasks.
    Provides:
        • structured graph metadata
        • cycle detection
        • safe node linking
        • ready-node resolution
        • graph introspection
        • future-proof hooks for branching + parallelism
    """

    def __init__(self, goal: str):
        self.goal = goal
        self.nodes: Dict[str, TaskNode] = {}
        self.entry_nodes: List[str] = []
        self.exit_nodes: List[str] = []
        self.created_at = time.time()

    # ------------------------------------------------------------
    # ADD NODE
    # ------------------------------------------------------------
    def add_node(self, node: TaskNode, is_entry: bool = False, is_exit: bool = False):
        self.nodes[node.id] = node

        if is_entry:
            self.entry_nodes.append(node.id)

        if is_exit:
            self.exit_nodes.append(node.id)

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

    # ------------------------------------------------------------
    # READY NODES
    # ------------------------------------------------------------
    def get_ready_nodes(self) -> List[TaskNode]:
        """
        Nodes whose parents are all done and which are still pending.
        """

        ready = []
        for node in self.nodes.values():
            if node.status == "pending":
                if all(self.nodes[p].status == "done" for p in node.parents):
                    ready.append(node)
        return ready

    # ------------------------------------------------------------
    # COMPLETION CHECK
    # ------------------------------------------------------------
    def is_complete(self) -> bool:
        return all(n.status in ("done", "error") for n in self.nodes.values())

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

        return any(dfs(nid) for nid in self.nodes)

    # ------------------------------------------------------------
    # GRAPH SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of the graph.
        """

        try:
            return {
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

        except Exception as e:
            return {
                "ok": False,
                "goal": self.goal,
                "node_count": len(self.nodes),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

