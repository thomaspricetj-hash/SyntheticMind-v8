# syntheticmind/taskgraph/task_graph_executor.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from .graph import TaskGraph, TaskNode


class TaskGraphExecutor:
    """
    Executes a TaskGraph using the MetaModelRuntime subsystems.
    Provides:
        • structured envelopes
        • per-node latency
        • safe execution
        • refined reasoning integration
        • future-proof node types
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    # ------------------------------------------------------------
    # NODE EXECUTION HELPERS
    # ------------------------------------------------------------
    def _run_reason(self, node: TaskNode):
        prompt = node.payload.get("prompt", "")
        result = self.runtime.generate(
            text=prompt,
            intent="small_reasoning",
        )
        node.result = result.get("output", result)
        node.status = "done"

    def _run_refine(self, node: TaskNode, graph: TaskGraph):
        if not node.parents:
            node.result = "[refine-error] no parent"
            node.status = "error"
            return

        parent = graph.nodes[node.parents[-1]]
        original_output = parent.result or ""

        refined = self.runtime.refiner.refine(
            prompt=graph.goal,
            output=original_output,
            passes=2,
        )

        node.result = refined
        node.status = "done"

    def _run_summary(self, node: TaskNode, graph: TaskGraph):
        parts = []
        for n in graph.nodes.values():
            if n.result:
                parts.append(f"{n.type.upper()}:\n{n.result}\n")

        summary_prompt = (
            "Summarize the following task graph results into a clear final answer:\n\n"
            + "\n".join(parts)
        )

        result = self.runtime.generate(
            text=summary_prompt,
            intent="small_reasoning",
        )

        node.result = result.get("output", result)
        node.status = "done"

    # ------------------------------------------------------------
    # INTERNAL: EXECUTE A SINGLE NODE
    # ------------------------------------------------------------
    def _execute_node(self, node: TaskNode, graph: TaskGraph):
        node.status = "running"
        node.started_at = time.time()

        try:
            if node.type == "reason":
                self._run_reason(node)
            elif node.type == "refine":
                self._run_refine(node, graph)
            elif node.type == "summary":
                self._run_summary(node, graph)
            else:
                node.result = f"[taskgraph-error] unknown node type: {node.type}"
                node.status = "error"

        except Exception as e:
            node.result = f"[taskgraph-exception] {e}"
            node.status = "error"
            node.error = str(e)

        finally:
            node.latency_ms = int((time.time() - node.started_at) * 1000)

    # ------------------------------------------------------------
    # MAIN EXECUTION LOOP
    # ------------------------------------------------------------
    def run(self, graph: TaskGraph) -> Dict[str, Any]:
        """
        Execute until all nodes are done or errored.
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "goal": str,
                "final": Any,
                "nodes": {...},
                "error": None
            }
        """

        start = time.time()

        try:
            while not graph.is_complete():
                ready = graph.get_ready_nodes()
                if not ready:
                    break  # deadlock or all done

                for node in ready:
                    self._execute_node(node, graph)

            # Collect exit node results
            exits = [graph.nodes[nid].result for nid in graph.exit_nodes]
            final = exits[-1] if exits else None

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": graph.goal,
                "final": final,
                "nodes": {
                    nid: {
                        "type": n.type,
                        "status": n.status,
                        "result": n.result,
                        "error": n.error,
                        "parents": n.parents,
                        "children": n.children,
                        "latency_ms": getattr(n, "latency_ms", None),
                    }
                    for nid, n in graph.nodes.items()
                },
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": graph.goal,
                "final": None,
                "nodes": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

