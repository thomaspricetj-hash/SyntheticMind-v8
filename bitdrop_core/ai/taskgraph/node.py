# syntheticmind/taskgraph/node.py

from __future__ import annotations
from typing import Dict, Any, List, Optional
import uuid
import time
import traceback


class TaskNode:
    """
    A single node in the TaskGraph.

    Types (suggested):
        - "reason"   : LLM reasoning
        - "tool"     : tool call
        - "vision"   : vision call
        - "refine"   : self-refine
        - "summary"  : summarize results
        - "simulate" : simulation step
        - "skill"    : skill execution
        - "branch"   : branching logic
    """

    def __init__(
        self,
        node_type: str,
        payload: Dict[str, Any],
        node_id: Optional[str] = None,
    ):
        self.id = node_id or str(uuid.uuid4())
        self.type = node_type
        self.payload = payload

        # Graph structure
        self.parents: List[str] = []
        self.children: List[str] = []

        # Execution state
        self.status: str = "pending"  # pending, running, done, error
        self.result: Any = None
        self.error: Optional[str] = None

        # Timing
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.latency_ms: Optional[int] = None

        # Metadata
        self.metadata: Dict[str, Any] = {
            "attempts": 0,
            "retries": 0,
            "notes": [],
        }

    # ------------------------------------------------------------
    # GRAPH LINKING
    # ------------------------------------------------------------
    def add_child(self, child_id: str):
        if child_id not in self.children:
            self.children.append(child_id)

    def add_parent(self, parent_id: str):
        if parent_id not in self.parents:
            self.parents.append(parent_id)

    # ------------------------------------------------------------
    # EXECUTION MARKERS
    # ------------------------------------------------------------
    def mark_running(self):
        self.status = "running"
        self.started_at = time.time()
        self.metadata["attempts"] += 1

    def mark_done(self, result: Any):
        self.status = "done"
        self.result = result
        if self.started_at:
            self.latency_ms = int((time.time() - self.started_at) * 1000)

    def mark_error(self, error: str):
        self.status = "error"
        self.error = error
        if self.started_at:
            self.latency_ms = int((time.time() - self.started_at) * 1000)

    # ------------------------------------------------------------
    # SAFE SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured, error-safe node snapshot.
        """

        try:
            return {
                "ok": True,
                "id": self.id,
                "type": self.type,
                "status": self.status,
                "parents": self.parents,
                "children": self.children,
                "result": self.result,
                "error": self.error,
                "latency_ms": self.latency_ms,
                "created_at": self.created_at,
                "metadata": self.metadata,
            }
        except Exception as e:
            return {
                "ok": False,
                "id": self.id,
                "type": self.type,
                "status": self.status,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

