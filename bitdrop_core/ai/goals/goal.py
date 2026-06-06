# ai/goals/goal.py

from __future__ import annotations
import uuid
import time
from typing import Optional, Dict, Any, List


class Goal:
    """
    A persistent long‑term objective with:
        • lifecycle state
        • progress tracking
        • metadata (tags, priority, category)
        • history of updates
        • deadlines + lateness detection
        • confidence scoring
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

        # Timestamps
        now = time.time()
        self.created_at = now
        self.updated_at = now

        # Lifecycle
        self.status = "pending"
        self.progress: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # Optional metadata fields
        self.priority = self.metadata.get("priority", "normal")  # low, normal, high, critical
        self.tags = self.metadata.get("tags", [])
        self.category = self.metadata.get("category", None)
        self.deadline = self.metadata.get("deadline", None)  # timestamp or None
        self.confidence = float(self.metadata.get("confidence", 1.0))

        # Archival flag (used by GoalStore)
        self.archived = False

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

    def mark_running(self):
        self.set_status("running")

    def mark_done(self):
        self.set_status("done")

    def mark_blocked(self, reason: str):
        self.set_status("blocked")
        self.progress["blocked_reason"] = reason
        self._touch()

    def mark_error(self, error: str):
        self.set_status("error")
        self.progress["error"] = error
        self._touch()

    # ------------------------------------------------------------
    # PROGRESS TRACKING
    # ------------------------------------------------------------

    def update(self, progress: Dict[str, Any]):
        """
        Update progress fields.
        Example:
            goal.update({"percent": 40, "step": "collecting data"})
        """
        old = dict(self.progress)
        self.progress.update(progress)
        self._record_history({"progress_from": old, "progress_to": dict(self.progress)})
        self._touch()

    def percent(self) -> float:
        """Return progress percent if available."""
        return float(self.progress.get("percent", 0.0))

    # ------------------------------------------------------------
    # DEADLINE / TIME AWARENESS
    # ------------------------------------------------------------

    def is_late(self) -> bool:
        """Return True if the goal has a deadline and is past it."""
        if not self.deadline:
            return False
        return time.time() > self.deadline and self.status != "done"

    def time_remaining(self) -> Optional[float]:
        """Seconds until deadline, or None if no deadline."""
        if not self.deadline:
            return None
        return self.deadline - time.time()

    # ------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization for GoalStore."""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "archived": self.archived,
            "history": self.history,
        }

