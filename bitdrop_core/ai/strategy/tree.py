# syntheticmind/strategy/strategy_tree_builder.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class StrategyTree3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# STRATEGY TREE BUILDER — MAX SPEED + 3D‑MAX
# ============================================================

class StrategyTreeBuilder:
    """
    Builds structured decision trees from linear plans (3D‑MAX Edition).
    Provides:
        • structured envelopes
        • node metadata
        • depth tracking
        • safe execution
        • 3D‑MAX introspection
        • future-proof hooks for TaskGraphPlanner
    """

    def __init__(self):
        self._last_3d: Optional[StrategyTree3D] = None

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

            nodes: Dict[str, Any] = {}

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
                        "length": len(text),
                    },
                }

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = StrategyTree3D(
                axis_x="build_tree",
                axis_y=[f"steps:{len(steps)}"],
                axis_z={
                    "latency_ms": latency,
                    "root": "step_0" if nodes else None,
                    "node_count": len(nodes),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "root": "step_0" if nodes else None,
                "nodes": nodes,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = StrategyTree3D(
                axis_x="build_tree",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "root": None,
                "nodes": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
