# syntheticmind/taskgraph/task_graph_planner.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from ..metamodel.ollama_client import OllamaClient
from .graph import TaskGraph
from .node import TaskNode


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class TaskGraphPlanner3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TASK GRAPH PLANNER — MAX SPEED + 3D‑MAX
# ============================================================

class TaskGraphPlanner:
    """
    Converts a natural language goal into a TaskGraph (3D‑MAX Edition).
    Provides:
        • structured envelopes
        • LLM-assisted plan drafting
        • safe fallback linear graphs
        • future-proof node types
        • metadata-rich graph construction
        • benchmark-compatible plan() returning a list of steps
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.llm = OllamaClient()
        self.model = "qwen2.5:1.5b"
        self._last_3d: Optional[TaskGraphPlanner3D] = None

    # ------------------------------------------------------------
    # INTERNAL: LLM PLAN DRAFT
    # ------------------------------------------------------------
    def _draft_plan(self, goal: str) -> List[str]:
        start = time.time()

        try:
            prompt = (
                "Break the following goal into 3–6 clear steps. "
                "Return ONLY a JSON list of strings.\n\n"
                f"Goal: {goal}"
            )

            resp = self.llm.generate(self.model, prompt)

            if isinstance(resp, list):
                steps = [str(x) for x in resp]
            elif isinstance(resp, dict) and "steps" in resp:
                steps = [str(x) for x in resp["steps"]]
            else:
                raise ValueError("invalid LLM response")

            self._last_3d = TaskGraphPlanner3D(
                axis_x="_draft_plan",
                axis_y=[f"goal_len:{len(goal)}"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "steps": len(steps),
                    "fallback": False,
                },
            )

            return steps

        except Exception:
            # Deterministic fallback
            steps = [
                f"Understand the goal: {goal}",
                "Break it into actionable steps",
                "Execute the steps in order",
            ]

            self._last_3d = TaskGraphPlanner3D(
                axis_x="_draft_plan",
                axis_y=["fallback"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "steps": len(steps),
                    "fallback": True,
                },
            )

            return steps

    # ------------------------------------------------------------
    # BENCHMARK ENTRYPOINT: RETURN JUST THE STEPS
    # ------------------------------------------------------------
    def plan(self, goal: str) -> List[str]:
        steps = self._draft_plan(goal)

        self._last_3d = TaskGraphPlanner3D(
            axis_x="plan",
            axis_y=[f"steps:{len(steps)}"],
            axis_z={"ok": True},
        )

        return steps

    # ------------------------------------------------------------
    # FULL GRAPH BUILDER (RICH API FOR RUNTIME)
    # ------------------------------------------------------------
    def build_graph(self, goal: str) -> Dict[str, Any]:
        start = time.time()

        try:
            # 1) DRAFT PLAN
            steps = self._draft_plan(goal)

            # 2) BUILD GRAPH
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

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = TaskGraphPlanner3D(
                axis_x="build_graph",
                axis_y=[f"steps:{len(steps)}"],
                axis_z={
                    "latency_ms": latency,
                    "node_count": len(graph.nodes),
                    "entry_count": len(graph.entry_nodes),
                    "exit_count": len(graph.exit_nodes),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "goal": goal,
                "graph": graph,
                "steps": steps,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = TaskGraphPlanner3D(
                axis_x="build_graph",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "goal": goal,
                "graph": None,
                "steps": [],
                "error": str(e),
                "traceback": traceback.format_exc(),
            }



