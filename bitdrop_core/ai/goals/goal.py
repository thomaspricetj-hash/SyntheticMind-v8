# ai/goals/goal.py

from __future__ import annotations
import uuid
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Goal3D:
    """
    3D structural view of a goal operation.

    axis_x: high-level operation ("init", "status", "update", "serialize")
    axis_y: structural decomposition (status, percent, tags)
    axis_z: metadata (timestamps, priority, category, deadline, confidence)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# GOAL (3D‑MAX)
# ============================================================

class Goal:
    """
    A persistent long‑term objective with:
        • lifecycle state
        • progress tracking
        • metadata (tags, priority, category)
        • history of updates
        • deadlines + lateness detection
        • confidence scoring
    Now 3D‑MAX introspectable.
    """

    VALID_STATUSES = {"pending", "running", "blocked", "done", "error"}

    def __init__(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        goal_id: Optional[str] = None
    ):
        self.id = goal_id or str(uuid.uuid4())
        self.text = text.strip()
        self.metadata = metadata or {}

        now = time.time()
        self.created_at = now
        self.updated_at = now

        self.status = "pending"
        self.progress: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        self.priority = self.metadata.get("priority", "normal")
        self.tags = self.metadata.get("tags", [])
        self.category = self.metadata.get("category", None)
        self.deadline = self.metadata.get("deadline", None)
        self.confidence = float(self.metadata.get("confidence", 1.0))

        self.archived = False

        self._last_3d: Optional[Goal3D] = Goal3D(
            axis_x="init",
            axis_y=[f"status:{self.status}", f"priority:{self.priority}"],
            axis_z={
                "goal_id": self.id,
                "created_at": self.created_at,
                "tags": list(self.tags),
                "category": self.category,
                "deadline": self.deadline,
                "confidence": self.confidence,
            },
        )

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _record_history(self, change: Dict[str, Any]):
        change["ts"] = time.time()
        self.history.append(change)

    def _touch(self):
        self.updated_at = time.time()

    # ------------------------------------------------------------
    # LIFECYCLE OPERATIONS
    # ------------------------------------------------------------

    def set_status(self, status: str):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid goal status: {status}")

        old = self.status
        self.status = status
        self._record_history({"status_from": old, "status_to": status})
        self._touch()

        self._last_3d = Goal3D(
            axis_x="status",
            axis_y=[f"from:{old}", f"to:{status}"],
            axis_z={
                "goal_id": self.id,
                "updated_at": self.updated_at,
                "percent": self.percent(),
                "deadline": self.deadline,
                "is_late": self.is_late(),
            },
        )

    def mark_running(self):
        self.set_status("running")

    def mark_done(self):
        self.set_status("done")

    def mark_blocked(self, reason: str):
        self.set_status("blocked")
        self.progress["blocked_reason"] = reason
        self._touch()

        self._last_3d = Goal3D(
            axis_x="status",
            axis_y=["blocked"],
            axis_z={
                "reason": reason,
                "goal_id": self.id,
                "updated_at": self.updated_at,
            },
        )

    def mark_error(self, error: str):
        self.set_status("error")
        self.progress["error"] = error
        self._touch()

        self._last_3d = Goal3D(
            axis_x="status",
            axis_y=["error"],
            axis_z={
                "error": error,
                "goal_id": self.id,
                "updated_at": self.updated_at,
            },
        )

    # ------------------------------------------------------------
    # PROGRESS TRACKING
    # ------------------------------------------------------------

    def update(self, progress: Dict[str, Any]):
        old = dict(self.progress)
        self.progress.update(progress)
        self._record_history({"progress_from": old, "progress_to": dict(self.progress)})
        self._touch()

        self._last_3d = Goal3D(
            axis_x="update",
            axis_y=[f"status:{self.status}", f"percent:{self.percent()}"],
            axis_z={
                "goal_id": self.id,
                "updated_at": self.updated_at,
                "progress_keys": list(progress.keys()),
                "deadline": self.deadline,
                "is_late": self.is_late(),
            },
        )

    def percent(self) -> float:
        return float(self.progress.get("percent", 0.0))

    # ------------------------------------------------------------
    # DEADLINE / TIME AWARENESS
    # ------------------------------------------------------------

    def is_late(self) -> bool:
        if not self.deadline:
            return False
        return time.time() > self.deadline and self.status != "done"

    def time_remaining(self) -> Optional[float]:
        if not self.deadline:
            return None
        return self.deadline - time.time()

    # ------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "text": self.text,
            "metadata": self.metadata,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "history": self.history,
        }

        self._last_3d = Goal3D(
            axis_x="serialize",
            axis_y=[f"status:{self.status}", f"percent:{self.percent()}"],
            axis_z={
                "goal_id": self.id,
                "history_len": len(self.history),
                "tags": list(self.tags),
                "priority": self.priority,
                "category": self.category,
            },
        )

        return out


