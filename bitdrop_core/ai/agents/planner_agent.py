# ai/agents/planner_agent.py

from __future__ import annotations
from .base import Agent


class PlannerAgent(Agent):
    """
    High‑level planner that converts goals or prompts into TaskGraphs.
    """

    name = "planner"
    description = "Decomposes goals into task graphs."
    capabilities = {
        "planning": True,
        "decomposition": True,
        "graph_generation": True,
        "reasoning": True,
    }

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, goal: str):
        """
        Core planning logic.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks
        """

        planner = getattr(self.runtime, "taskgraph_planner", None)
        if planner is None or not hasattr(planner, "plan"):
            return {
                "error": "TaskGraph planner unavailable",
                "goal": goal,
            }

        # Generate a TaskGraph from the goal text
        graph = planner.plan(goal)

        return {
            "goal": goal,
            "graph": graph,
        }

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could log planning intent or attach metadata
        pass

    def _post_run(self, result, success: bool):
        # Store planning events in memory
        if success and isinstance(result, dict) and "goal" in result:
            self.runtime.memory.remember(
                f"[planner] planned goal: {result['goal']}"
            )

