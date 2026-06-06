# syntheticmind/taskgraph/task_graph_planner.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback

from ..metamodel.ollama_client import OllamaClient
from .graph import TaskGraph
from .node import TaskNode


class TaskGraphPlanner:
    """
    Converts a natural language goal into a TaskGraph.
    Provides:
        • structured envelopes
        • LLM-assisted plan drafting
        • safe fallback linear graphs
        • future-proof node types
        • metadata-rich graph construction
    """

    def __init__(self):
        self.llm = OllamaClient()
        self.model = "qwen2.5:1.5b"

    # ------------------------------------------------------------
    # INTERNAL: LLM PLAN DRAFT
    # ------------------------------------------------------------
    def _draft_plan(self, goal: str) -> List[str]:
        """
        Try to get a multi-step plan from the LLM.
        Fallback: single-step plan.
        """

        try:
            prompt = (
                "Break the following goal into 3–6 clear steps. "
                "Return ONLY a JSON list of strings.\n\n"
                f"Goal: {goal}"
            )

            resp = self.llm.generate(self.model, prompt)
            if isinstance(resp, list):
                return [str(x) for x in resp]

            if isinstance(resp, dict) and "steps" in resp:
                return [str(x) for x in resp["steps"]]

        except Exception:
            pass

        # Fallback
        return [f"Work toward: {goal}"]

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT: BUILD GRAPH
    # ------------------------------------------------------------
    def plan(self, goal: str) -> Dict[str, Any]:
        """
        Build a TaskGraph for the given goal.
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "goal": str,
                "graph": TaskGraph,
                "error": None
            }
        """

        start = time.time()

        try:
            # ----------------------------------------------------
            # 1) DRAFT PLAN
            # ----------------------------------------------------
            steps = self._draft_plan(goal)

            # ----------------------------------------------------
            # 2) BUILD GRAPH
            # ----------------------------------------------------
            graph = TaskGraph(goal=goal)

            # Node 1: reasoning
            n1 = TaskNode(
                node_type="reason",
                payload={"prompt": goal},
            )
            graph.add_node(n1, is_entry=True)

            # Node 2: refinement
            n2 = TaskNode(
                node_type="refine",
                payload={},
            )
            graph.add_node(n2)

            # Node 3: summary
            n3 = TaskNode(
                node_type="summary",
                payload={},
            )
            graph.add_node(n3, is_exit=True)

            # Link nodes
            graph.link(n1.id, n2.id)
            graph.link(n2.id, n3.id)

            # ----------------------------------------------------
            # FINAL STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": goal,
                "graph": graph,
                "steps_used": steps,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": goal,
                "graph": None,
                "steps_used": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

