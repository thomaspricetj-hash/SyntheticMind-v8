# syntheticmind/strategy/strategy_tree_builder.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class StrategyTreeBuilder:
    """
    Builds structured decision trees from linear plans.
    Provides:
        • structured envelopes
        • node metadata
        • depth tracking
        • safe execution
        • future-proof hooks for TaskGraphPlanner
    """

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def build_tree(self, steps: List[str]) -> Dict[str, Any]:
        """
        steps: list of step descriptions

        Returns a structured tree envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "root": str | None,
                "nodes": {id: {...}},
                "error": None
            }
        """

        start = time.time()

        try:
            if not isinstance(steps, list):
                raise ValueError("steps must be a list of strings")

            nodes = {}
            for idx, text in enumerate(steps):
                node_id = f"step_{idx}"

                nodes[node_id] = {
                    "id": node_id,
                    "text": text,
                    "depth": idx,
                    "type": "action",
                    "next": f"step_{idx + 1}" if idx + 1 < len(steps) else None,
                    "fallback": None,
                    "metadata": {
                        "complexity": len(text.split()),
                        "index": idx,
                    },
                }

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "root": "step_0" if nodes else None,
                "nodes": nodes,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "root": None,
                "nodes": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
