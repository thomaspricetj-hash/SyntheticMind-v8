from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Simulation3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SIMULATION ENGINE — MAX SPEED + 3D‑MAX
# ============================================================

class SimulationEngine:
    """
    Core simulation engine for counterfactual reasoning and multi-step rollouts.
    3D‑MAX Edition:
        • structured envelopes
        • latency measurement
        • safe execution
        • packet-aware runtime calls
        • future-proof simulation hooks
        • 3D‑MAX introspection for every simulation cycle
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self._last_3d: Simulation3D | None = None

    # ------------------------------------------------------------
    # MULTI-STEP SIMULATION
    # ------------------------------------------------------------
    def simulate_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
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

            latency = int((time.time() - start) * 1000)
            self._last_3d = Simulation3D(
                axis_x="simulate_steps",
                axis_y=[f"steps:{len(steps)}"],
                axis_z={
                    "latency_ms": latency,
                    "ok": True,
                    "compressed_count": sum(1 for s in steps if s.get("compressed")),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "steps": results,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Simulation3D(
                axis_x="simulate_steps",
                axis_y=[f"steps:{len(steps)}"],
                axis_z={"latency_ms": latency, "ok": False, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "steps": results,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

