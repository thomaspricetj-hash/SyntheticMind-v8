# ai/goals/store.py

from __future__ import annotations
import json
import os
import time
from typing import Dict, List, Optional
from .goal import Goal


class GoalStore:
    """
    Persistent, fault‑tolerant goal storage with:
        • atomic save/load
        • metadata preservation
        • filtering & search
        • soft deletion
        • update history
    """

    def __init__(self, path: str = "bitdrop_goals.json"):
        self.path = path
        self.goals: Dict[str, Goal] = {}
        self._load()

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _load(self):
        """Load goals from disk safely."""
        if not os.path.exists(self.path):
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            for gid, g in raw.items():
                goal = Goal(
                    text=g.get("text", ""),
                    metadata=g.get("metadata", {}),
                    goal_id=gid
                )
                goal.status = g.get("status", "pending")
                goal.progress = g.get("progress", 0.0)
                goal.created_at = g.get("created_at", time.time())
                goal.updated_at = g.get("updated_at", goal.created_at)
                goal.archived = g.get("archived", False)
                goal.history = g.get("history", [])

                self.goals[gid] = goal

        except Exception:
            # Corrupted file → rename and start fresh
            corrupt = self.path + ".corrupt"
            try:
                os.rename(self.path, corrupt)
            except Exception:
                pass

    def _save(self):
        """Atomic save to prevent corruption."""
        tmp_path = self.path + ".tmp"

        raw = {
            gid: {
                "text": g.text,
                "metadata": g.metadata,
                "status": g.status,
                "progress": g.progress,
                "created_at": g.created_at,
                "updated_at": g.updated_at,
                "archived": getattr(g, "archived", False),
                "history": getattr(g, "history", []),
            }
            for gid, g in self.goals.items()
        }

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

            os.replace(tmp_path, self.path)
        except Exception:
            # If atomic replace fails, fallback to direct write
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def add(self, goal: Goal):
        """Add a new goal."""
        self.goals[goal.id] = goal
        self._save()

    def update(self, goal: Goal):
        """Update an existing goal and append history."""
        if goal.id in self.goals:
            old = self.goals[goal.id]

            # Track changes
            change = {
                "ts": time.time(),
                "old_status": old.status,
                "new_status": goal.status,
                "old_progress": old.progress,
                "new_progress": goal.progress,
            }
            goal.history.append(change)

        goal.updated_at = time.time()
        self.goals[goal.id] = goal
        self._save()

    def get(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)

    def list(self, include_archived: bool = False) -> List[Goal]:
        """Return all goals, optionally including archived ones."""
        if include_archived:
            return list(self.goals.values())
        return [g for g in self.goals.values() if not getattr(g, "archived", False)]

    # ------------------------------------------------------------
    # SEARCH / FILTER
    # ------------------------------------------------------------

    def search(self, text: str) -> List[Goal]:
        """Return goals whose text contains the query."""
        text = text.lower()
        return [g for g in self.goals.values() if text in g.text.lower()]

    def filter_by_status(self, status: str) -> List[Goal]:
        return [g for g in self.goals.values() if g.status == status]

    def filter_by_tag(self, tag: str) -> List[Goal]:
        return [
            g for g in self.goals.values()
            if tag in g.metadata.get("tags", [])
        ]

    # ------------------------------------------------------------
    # ARCHIVAL / DELETION
    # ------------------------------------------------------------

    def archive(self, goal_id: str):
        """Soft-delete a goal (kept for history)."""
        g = self.goals.get(goal_id)
        if g:
            g.archived = True
            g.updated_at = time.time()
            self._save()

    def delete(self, goal_id: str):
        """Hard delete."""
        if goal_id in self.goals:
            del self.goals[goal_id]
            self._save()

