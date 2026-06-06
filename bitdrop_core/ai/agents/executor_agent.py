# ai/agents/executor_agent.py

from __future__ import annotations
from .base import Agent


class ExecutorAgent(Agent):
    """
    Executes TaskGraphs using the runtime's taskgraph_executor.
    """

    name = "executor"
    description = "Executes task graph nodes."
    capabilities = {
        "execute_graph": True,
        "parallel_tasks": True,
        "tool_integration": True,
    }

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, graph):
        """
        Core execution logic.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks
        """

        executor = getattr(self.runtime, "taskgraph_executor", None)
        if executor is None or not hasattr(executor, "run"):
            return {
                "error": "TaskGraph executor unavailable",
                "graph": str(graph),
            }

        # Execute the graph
        result = executor.run(graph)

        return {
            "graph": str(graph),
            "result": result,
        }

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could log, warm up GPU, or attach execution metadata
        pass

    def _post_run(self, result, success: bool):
        # Could store execution summary in memory
        if success:
            self.runtime.memory.remember("[executor] executed a task graph")

