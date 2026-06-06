# ai/goals/manager.py

from __future__ import annotations
from typing import Optional, Dict, Any, List
from .goal import Goal
from .store import GoalStore


class GoalManager:
    """
    High-level interface for creating, updating, executing, and resuming goals.
    Integrates with:
        • TaskGraph planner
        • TaskGraph executor
        • Agents subsystem
        • Persistent GoalStore
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.store = GoalStore()

    # ------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------

    def create(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Goal:
        """Create a new goal with metadata (priority, tags, category, etc.)."""
        goal = Goal(text=text, metadata=metadata)
        self.store.add(goal)
        self._log(f"[GoalManager] Created goal {goal.id}: {goal.text}")
        return goal

    # ------------------------------------------------------------
    # UPDATES
    # ------------------------------------------------------------

    def update(self, goal_id: str, progress: Dict[str, Any]) -> Optional[Goal]:
        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.update(progress)
        self.store.update(goal)
        self._log(f"[GoalManager] Updated goal {goal.id}: {progress}")
        return goal

    def complete(self, goal_id: str) -> Optional[Goal]:
        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_done()
        self.store.update(goal)
        self._log(f"[GoalManager] Completed goal {goal.id}")
        return goal

    def error(self, goal_id: str, error: str) -> Optional[Goal]:
        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_error(error)
        self.store.update(goal)
        self._log(f"[GoalManager] Goal {goal.id} errored: {error}")
        return goal

    # ------------------------------------------------------------
    # EXECUTION / RESUMPTION
    # ------------------------------------------------------------

    def resume(self, goal_id: str):
        """
        Re-run the goal using TaskGraph + Agents.
        Automatically updates progress and status.
        """

        goal = self.store.get(goal_id)
        if not goal:
            return None

        goal.mark_running()
        self.store.update(goal)

        self._log(f"[GoalManager] Resuming goal {goal.id}: {goal.text}")

        try:
            # 1. Plan
            graph = self.runtime.taskgraph_planner.plan(goal.text)

            # 2. Execute
            result = self.runtime.taskgraph_executor.run(graph)

            # 3. Update goal
            goal.update({"last_run": result})
            goal.mark_done()
            self.store.update(goal)

            self._log(f"[GoalManager] Goal {goal.id} completed via resume()")
            return result

        except Exception as e:
            goal.mark_error(str(e))
            self.store.update(goal)
            self._log(f"[GoalManager] Goal {goal.id} failed during resume: {e}")
            return None

    # ------------------------------------------------------------
    # LISTING / SEARCH
    # ------------------------------------------------------------

    def list(self, include_archived: bool = False) -> List[Goal]:
        return self.store.list(include_archived=include_archived)

    def search(self, text: str) -> List[Goal]:
        """Search goals by text content."""
        return self.store.search(text)

    def by_status(self, status: str) -> List[Goal]:
        """Filter goals by lifecycle state."""
        return self.store.filter_by_status(status)

    def by_tag(self, tag: str) -> List[Goal]:
        """Filter goals by metadata tag."""
        return self.store.filter_by_tag(tag)

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _log(self, msg: str):
        """Runtime-safe logging hook."""
        try:
            self.runtime.log(msg)
        except Exception:
            print(msg)

