# syntheticmind/taskgraph/node.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import uuid
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class TaskNode3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TASK NODE — MAX STRUCT + 3D‑MAX
# ============================================================

class TaskNode:
    """
    A single node in the TaskGraph (3D‑MAX Edition).

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

        # 3D‑MAX telemetry
        self._last_3d: Optional[TaskNode3D] = TaskNode3D(
            axis_x="init",
            axis_y=[f"type:{node_type}"],
            axis_z={"created_at": self.created_at},
        )

    # ------------------------------------------------------------
    # GRAPH LINKING
    # ------------------------------------------------------------
    def add_child(self, child_id: str):
        if child_id not in self.children:
            self.children.append(child_id)

        self._last_3d = TaskNode3D(
            axis_x="add_child",
            axis_y=[f"{self.id}->{child_id}"],
            axis_z={"child_count": len(self.children)},
        )

    def add_parent(self, parent_id: str):
        if parent_id not in self.parents:
            self.parents.append(parent_id)

        self._last_3d = TaskNode3D(
            axis_x="add_parent",
            axis_y=[f"{parent_id}->{self.id}"],
            axis_z={"parent_count": len(self.parents)},
        )

    # ------------------------------------------------------------
    # EXECUTION MARKERS
    # ------------------------------------------------------------
    def mark_running(self):
        self.status = "running"
        self.started_at = time.time()
        self.metadata["attempts"] += 1

        self._last_3d = TaskNode3D(
            axis_x="mark_running",
            axis_y=[f"node:{self.id}"],
            axis_z={"attempts": self.metadata["attempts"]},
        )

    def mark_done(self, result: Any):
        self.status = "done"
        self.result = result
        if self.started_at:
            self.latency_ms = int((time.time() - self.started_at) * 1000)

        self._last_3d = TaskNode3D(
            axis_x="mark_done",
            axis_y=[f"node:{self.id}"],
            axis_z={
                "latency_ms": self.latency_ms,
                "has_result": result is not None,
            },
        )

    def mark_error(self, error: str):
        self.status = "error"
        self.error = error
        if self.started_at:
            self.latency_ms = int((time.time() - self.started_at) * 1000)

        self._last_3d = TaskNode3D(
            axis_x="mark_error",
            axis_y=[f"node:{self.id}"],
            axis_z={
                "latency_ms": self.latency_ms,
                "error": error,
            },
        )

    # ------------------------------------------------------------
    # SAFE SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured, error-safe node snapshot.
        """

        try:
            snap = {
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

            self._last_3d = TaskNode3D(
                axis_x="snapshot",
                axis_y=[f"node:{self.id}"],
                axis_z={"status": self.status},
            )

            return snap

        except Exception as e:
            self._last_3d = TaskNode3D(
                axis_x="snapshot",
                axis_y=[f"node:{self.id}", "exception"],
                axis_z={"error": str(e)},
            )

            return {
                "ok": False,
                "id": self.id,
                "type": self.type,
                "status": self.status,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


