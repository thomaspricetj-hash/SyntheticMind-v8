# syntheticmind/metamodel/counterfactual_reasoner.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class CounterfactualReasoner:
    """
    Builds and evaluates counterfactual 'what if' scenarios.
    Integrates with the MetaModelRuntime for:
        • generation
        • simulation
        • structured envelopes
        • multi-variation analysis
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    # ------------------------------------------------------------
    # SINGLE SCENARIO BUILDER
    # ------------------------------------------------------------
    def build_scenario(self, base_text: str, variation: str) -> Dict[str, Any]:
        """
        Build a structured counterfactual scenario envelope.
        """

        prompt = f"What if {variation} instead of {base_text}?"

        return {
            "ok": True,
            "base": base_text,
            "variation": variation,
            "prompt": prompt,
            "error": None,
        }

    # ------------------------------------------------------------
    # GENERATE COUNTERFACTUAL ANSWER
    # ------------------------------------------------------------
    def generate(self, base_text: str, variation: str) -> Dict[str, Any]:
        """
        Build a scenario AND generate a counterfactual answer using the runtime.
        """

        start = time.time()

        try:
            scenario = self.build_scenario(base_text, variation)
            prompt = scenario["prompt"]

            # Use the runtime's reasoning pipeline
            result = self.runtime.ask(prompt)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "scenario": scenario,
                "counterfactual_output": result,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "scenario": None,
                "counterfactual_output": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # MULTI-VARIATION ANALYSIS
    # ------------------------------------------------------------
    def generate_many(self, base_text: str, variations: List[str]) -> Dict[str, Any]:
        """
        Generate multiple counterfactuals in one call.
        """

        start = time.time()
        results = []

        try:
            for v in variations:
                results.append(self.generate(base_text, v))

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "base": base_text,
                "results": results,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "base": base_text,
                "results": results,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
