# ai/goals/store.py

from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .goal import Goal


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class GoalStore3D:
    """
    3D structural view of a GoalStore operation.

    axis_x: high-level operation ("load", "save", "add", "update", "search", "filter", "archive", "delete")
    axis_y: structural decomposition (goal_count, op_target)
    axis_z: metadata (latency, path, keys, error)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, any]


# ============================================================
# GOAL STORE (3D‑MAX)
# ============================================================

class GoalStore:
    """
    Persistent, fault‑tolerant goal storage with:
        • atomic save/load
        • metadata preservation
        • filtering & search
        • soft deletion
        • update history
    Now 3D‑MAX introspectable.
    """

    def __init__(self, path: str = "bitdrop_goals.json"):
        self.path = path
        self.goals: Dict[str, Goal] = {}
        self._last_3d: Optional[GoalStore3D] = None
        self._load()

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _load(self):
        start = time.time()

        if not os.path.exists(self.path):
            self._last_3d = GoalStore3D(
                axis_x="load",
                axis_y=["file_missing"],
                axis_z={"path": self.path, "latency_ms": int((time.time() - start) * 1000)},
            )
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
                goal.progress = g.get("progress", {})
                goal.created_at = g.get("created_at", time.time())
                goal.updated_at = g.get("updated_at", goal.created_at)
                goal.archived = g.get("archived", False)
                goal.history = g.get("history", [])

                self.goals[gid] = goal

            self._last_3d = GoalStore3D(
                axis_x="load",
                axis_y=[f"goals:{len(self.goals)}"],
                axis_z={"path": self.path, "latency_ms": int((time.time() - start) * 1000)},
            )

        except Exception as e:
            corrupt = self.path + ".corrupt"
            try:
                os.rename(self.path, corrupt)
            except Exception:
                pass

            self._last_3d = GoalStore3D(
                axis_x="load",
                axis_y=["corrupt_file"],
                axis_z={
                    "path": self.path,
                    "corrupt_path": corrupt,
                    "error": str(e),
                    "latency_ms": int((time.time() - start) * 1000),
                },
            )

    def _save(self):
        start = time.time()
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

            self._last_3d = GoalStore3D(
                axis_x="save",
                axis_y=[f"goals:{len(self.goals)}"],
                axis_z={"path": self.path, "latency_ms": int((time.time() - start) * 1000)},
            )

        except Exception as e:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2)

            self._last_3d = GoalStore3D(
                axis_x="save",
                axis_y=["fallback_write"],
                axis_z={
                    "path": self.path,
                    "error": str(e),
                    "latency_ms": int((time.time() - start) * 1000),
                },
            )

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def add(self, goal: Goal):
        self.goals[goal.id] = goal
        self._save()

        self._last_3d = GoalStore3D(
            axis_x="add",
            axis_y=[f"goal:{goal.id}"],
            axis_z={"count": len(self.goals)},
        )

    def update(self, goal: Goal):
        if goal.id in self.goals:
            old = self.goals[goal.id]
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

        self._last_3d = GoalStore3D(
            axis_x="update",
            axis_y=[f"goal:{goal.id}", f"status:{goal.status}"],
            axis_z={"progress_keys": list(goal.progress.keys())},
        )

    def get(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)

    def list(self, include_archived: bool = False) -> List[Goal]:
        goals = (
            list(self.goals.values())
            if include_archived
            else [g for g in self.goals.values() if not getattr(g, "archived", False)]
        )

        self._last_3d = GoalStore3D(
            axis_x="list",
            axis_y=[f"include_archived:{include_archived}"],
            axis_z={"count": len(goals)},
        )

        return goals

    # ------------------------------------------------------------
    # SEARCH / FILTER
    # ------------------------------------------------------------

    def search(self, text: str) -> List[Goal]:
        text = text.lower()
        results = [g for g in self.goals.values() if text in g.text.lower()]

        self._last_3d = GoalStore3D(
            axis_x="search",
            axis_y=[f"text_len:{len(text)}"],
            axis_z={"count": len(results)},
        )

        return results

    def filter_by_status(self, status: str) -> List[Goal]:
        results = [g for g in self.goals.values() if g.status == status]

        self._last_3d = GoalStore3D(
            axis_x="filter_by_status",
            axis_y=[f"status:{status}"],
            axis_z={"count": len(results)},
        )

        return results

    def filter_by_tag(self, tag: str) -> List[Goal]:
        results = [
            g for g in self.goals.values()
            if tag in g.metadata.get("tags", [])
        ]

        self._last_3d = GoalStore3D(
            axis_x="filter_by_tag",
            axis_y=[f"tag:{tag}"],
            axis_z={"count": len(results)},
        )

        return results

    # ------------------------------------------------------------
    # ARCHIVAL / DELETION
    # ------------------------------------------------------------

    def archive(self, goal_id: str):
        g = self.goals.get(goal_id)
        if g:
            g.archived = True
            g.updated_at = time.time()
            self._save()

            self._last_3d = GoalStore3D(
                axis_x="archive",
                axis_y=[f"goal:{goal_id}"],
                axis_z={"archived": True},
            )

    def delete(self, goal_id: str):
        if goal_id in self.goals:
            del self.goals[goal_id]
            self._save()

            self._last_3d = GoalStore3D(
                axis_x="delete",
                axis_y=[f"goal:{goal_id}"],
                axis_z={"remaining": len(self.goals)},
            )


