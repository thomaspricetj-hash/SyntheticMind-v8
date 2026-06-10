from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List

from .engine import SimulationEngine
from .counterfactual import CounterfactualReasoner
from .rollout import SimulationRollout


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Simulation3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SIMULATION MANAGER — MAX SPEED + 3D‑MAX
# ============================================================

class SimulationManager:
    """
    High‑level interface for simulation‑based reasoning (3D‑MAX Edition).

    Provides:
        • structured simulation envelopes
        • rollout scoring
        • counterfactual generation
        • 3D‑MAX introspection for every simulation cycle
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.engine = SimulationEngine(runtime)
        self.counterfactual = CounterfactualReasoner(runtime)
        self.rollout = SimulationRollout()
        self._last_3d: Simulation3D | None = None

    # ------------------------------------------------------------
    # PLAN SIMULATION
    # ------------------------------------------------------------
    def simulate_plan(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = self.engine.simulate_steps(steps)
        score = self.rollout.score(results)

        self._last_3d = Simulation3D(
            axis_x="simulate_plan",
            axis_y=[f"steps:{len(steps)}"],
            axis_z={
                "results_len": len(results),
                "score": score,
            },
        )

        return {
            "steps": steps,
            "results": results,
            "score": score,
        }

    # ------------------------------------------------------------
    # COUNTERFACTUAL SIMULATION
    # ------------------------------------------------------------
    def simulate_counterfactual(self, base_text: str, variation: str) -> Dict[str, Any]:
        scenario = self.counterfactual.build_scenario(base_text, variation)
        result = self.runtime.generate(
            text=scenario["prompt"],
            intent="small_reasoning"
        )

        self._last_3d = Simulation3D(
            axis_x="simulate_counterfactual",
            axis_y=[f"variation:{variation}"],
            axis_z={
                "prompt_len": len(scenario["prompt"]),
                "ok": True,
            },
        )

        return {
            "scenario": scenario,
            "result": result,
        }
