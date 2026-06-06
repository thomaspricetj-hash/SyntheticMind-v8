from typing import Dict, Any, List
from .engine import SimulationEngine
from .counterfactual import CounterfactualReasoner
from .rollout import SimulationRollout


class SimulationManager:
    """
    High-level interface for simulation-based reasoning.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.engine = SimulationEngine(runtime)
        self.counterfactual = CounterfactualReasoner(runtime)
        self.rollout = SimulationRollout()

    def simulate_plan(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = self.engine.simulate_steps(steps)
        score = self.rollout.score(results)
        return {
            "steps": steps,
            "results": results,
            "score": score,
        }

    def simulate_counterfactual(self, base_text: str, variation: str) -> Dict[str, Any]:
        scenario = self.counterfactual.build_scenario(base_text, variation)
        result = self.runtime.generate(text=scenario["prompt"], intent="small_reasoning")
        return {
            "scenario": scenario,
            "result": result,
        }
