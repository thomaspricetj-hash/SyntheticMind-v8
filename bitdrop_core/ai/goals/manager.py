# ai/goals/manager.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .goal import Goal
from .store import GoalStore


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class GoalManager3D:
    """
    3D structural view of a goal manager operation.

    axis_x: high-level operation ("create", "update", "complete", "error", "resume", "list", "search")
    axis_y: structural decomposition (goal_id, status, progress_keys)
    axis_z: metadata (latency, text_len, result_state, count)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# GOAL MANAGER (3D‑MAX)
# ============================================================

class GoalManager:
    """
    High-level interface for creating, updating, executing, and resuming goals.
    Integrates with:
        • TaskGraph planner
        • TaskGraph executor
        • Agents subsystem
        • Persistent GoalStore
    Now 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.store = GoalStore()
        self._last_3d: Optional[GoalManager3D] = None

    # ------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------

    def create(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Goal:
        start = self.runtime.now_ms() if hasattr(self.runtime, "now_ms") else None

        goal = Goal(text=text, metadata=metadata)
        self.store.add(goal)
        self._log(f"[GoalManager] Created goal {goal.id}: {goal.text}")

        latency = (
            (self.runtime.now_ms() - start) if start is not None else None
        )

        self._last_3d = GoalManager3D(
            axis_x="create",
            axis_y=[f"goal:{goal.id}", f"status:{goal.status}"],
            axis_z={
                "text_len": len(text),
                "latency_ms": latency,
                "tags": list(goal.tags),
                "priority": goal.priority,
            },
        )

        return goal

    # ------------------------------------------------------------
    # UPDATES
    # ------------------------------------------------------------

    def update(self, goal_id: str, progress: Dict[str, Any]) -> Optional[Goal]:
        start = self.runtime.now_ms() if hasattr(self.runtime, "now_ms") else None

        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.update(progress)
        self.store.update(goal)
        self._log(f"[GoalManager] Updated goal {goal.id}: {progress}")

        latency = (
            (self.runtime.now_ms() - start) if start is not None else None
        )

        self._last_3d = GoalManager3D(
            axis_x="update",
            axis_y=[f"goal:{goal.id}", f"status:{goal.status}"],
            axis_z={
                "progress_keys": list(progress.keys()),
                "percent": goal.percent(),
                "latency_ms": latency,
            },
        )

        return goal

    def complete(self, goal_id: str) -> Optional[Goal]:
        start = self.runtime.now_ms() if hasattr(self.runtime, "now_ms") else None

        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_done()
        self.store.update(goal)
        self._log(f"[GoalManager] Completed goal {goal.id}")

        latency = (
            (self.runtime.now_ms() - start) if start is not None else None
        )

        self._last_3d = GoalManager3D(
            axis_x="complete",
            axis_y=[f"goal:{goal.id}", "status:done"],
            axis_z={"latency_ms": latency},
        )

        return goal

    def error(self, goal_id: str, error: str) -> Optional[Goal]:
        start = self.runtime.now_ms() if hasattr(self.runtime, "now_ms") else None

        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_error(error)
        self.store.update(goal)
        self._log(f"[GoalManager] Goal {goal.id} errored: {error}")

        latency = (
            (self.runtime.now_ms() - start) if start is not None else None
        )

        self._last_3d = GoalManager3D(
            axis_x="error",
            axis_y=[f"goal:{goal.id}", "status:error"],
            axis_z={"error": error, "latency_ms": latency},
        )

        return goal

    # ------------------------------------------------------------
    # EXECUTION / RESUMPTION
    # ------------------------------------------------------------

    def resume(self, goal_id: str):
        start = self.runtime.now_ms() if hasattr(self.runtime, "now_ms") else None

        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_running()
        self.store.update(goal)

        self._log(f"[GoalManager] Resuming goal {goal.id}: {goal.text}")

        try:
            graph = self.runtime.taskgraph_planner.plan(goal.text)
            result = self.runtime.taskgraph_executor.run(graph)

            goal.update({"last_run": result})
            goal.mark_done()
            self.store.update(goal)

            self._log(f"[GoalManager] Goal {goal.id} completed via resume()")

            latency = (
                (self.runtime.now_ms() - start) if start is not None else None
            )

            self._last_3d = GoalManager3D(
                axis_x="resume",
                axis_y=[f"goal:{goal.id}", "status:done"],
                axis_z={
                    "latency_ms": latency,
                    "result_type": type(result).__name__,
                },
            )

            return result

        except Exception as e:
            goal.mark_error(str(e))
            self.store.update(goal)
            self._log(f"[GoalManager] Goal {goal.id} failed during resume: {e}")

            latency = (
                (self.runtime.now_ms() - start) if start is not None else None
            )

            self._last_3d = GoalManager3D(
                axis_x="resume",
                axis_y=[f"goal:{goal.id}", "status:error"],
                axis_z={"error": str(e), "latency_ms": latency},
            )

            return None

    # ------------------------------------------------------------
    # LISTING / SEARCH
    # ------------------------------------------------------------

    def list(self, include_archived: bool = False) -> List[Goal]:
        goals = self.store.list(include_archived=include_archived)

        self._last_3d = GoalManager3D(
            axis_x="list",
            axis_y=[f"include_archived:{include_archived}"],
            axis_z={"count": len(goals)},
        )

        return goals

    def search(self, text: str) -> List[Goal]:
        results = self.store.search(text)

        self._last_3d = GoalManager3D(
            axis_x="search",
            axis_y=[f"text_len:{len(text)}"],
            axis_z={"count": len(results)},
        )

        return results

    def by_status(self, status: str) -> List[Goal]:
        results = self.store.filter_by_status(status)

        self._last_3d = GoalManager3D(
            axis_x="by_status",
            axis_y=[f"status:{status}"],
            axis_z={"count": len(results)},
        )

        return results

    def by_tag(self, tag: str) -> List[Goal]:
        results = self.store.filter_by_tag(tag)

        self._last_3d = GoalManager3D(
            axis_x="by_tag",
            axis_y=[f"tag:{tag}"],
            axis_z={"count": len(results)},
        )

        return results

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _log(self, msg: str):
        try:
            self.runtime.log(msg)
        except Exception:
            print(msg)

