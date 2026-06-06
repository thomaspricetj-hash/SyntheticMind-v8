# syntheticmind/metamodel/simulation_engine.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class SimulationEngine:
    """
    Core simulation engine for counterfactual reasoning and multi-step rollouts.
    Provides:
        • structured envelopes
        • latency measurement
        • safe execution
        • packet-aware runtime calls
        • future-proof simulation hooks
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    # ------------------------------------------------------------
    # MULTI-STEP SIMULATION
    # ------------------------------------------------------------
    def simulate_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Each step:
            {
                "text": str,
                "intent": str,
                "metadata": dict,
                "compressed": bool,
                "return_compressed": bool
            }

        Returns a structured simulation envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "steps": [...],
                "error": str | None
            }
        """

        start = time.time()
        results = []

        try:
            for i, step in enumerate(steps):
                step_start = time.time()

                text = step.get("text", "")
                intent = step.get("intent", "small_reasoning")
                metadata = step.get("metadata", {})
                compressed = step.get("compressed", False)
                return_compressed = step.get("return_compressed", False)

                # Runtime call (packet-aware)
                result = self.runtime.generate(
                    text=text,
                    intent=intent,
                    metadata=metadata,
                    compressed=compressed,
                    return_compressed=return_compressed,
                )

                results.append(
                    {
                        "index": i,
                        "input": step,
                        "output": result,
                        "latency_ms": int((time.time() - step_start) * 1000),
                    }
                )

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "steps": results,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "steps": results,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
