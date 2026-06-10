from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Counterfactual3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# COUNTERFACTUAL REASONER — MAX SPEED + 3D‑MAX
# ============================================================

class CounterfactualReasoner:
    """
    CounterfactualReasoner — 3D‑MAX Edition

    Builds and evaluates counterfactual 'what if' scenarios.
    Integrates with the MetaModelRuntime for:
        • generation
        • simulation
        • structured envelopes
        • multi‑variation analysis
        • 3D‑MAX introspection for every scenario
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self._last_3d: Counterfactual3D | None = None

    # ------------------------------------------------------------
    # SINGLE SCENARIO BUILDER
    # ------------------------------------------------------------
    def build_scenario(self, base_text: str, variation: str) -> Dict[str, Any]:
        prompt = f"What if {variation} instead of {base_text}?"

        self._last_3d = Counterfactual3D(
            axis_x="build_scenario",
            axis_y=[f"base_len:{len(base_text)}", f"variation_len:{len(variation)}"],
            axis_z={"prompt_len": len(prompt)},
        )

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
        start = time.time()

        try:
            scenario = self.build_scenario(base_text, variation)
            prompt = scenario["prompt"]

            result = self.runtime.ask(prompt)

            latency = int((time.time() - start) * 1000)
            self._last_3d = Counterfactual3D(
                axis_x="generate",
                axis_y=[f"variation:{variation}"],
                axis_z={"latency_ms": latency, "ok": True},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "scenario": scenario,
                "counterfactual_output": result,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Counterfactual3D(
                axis_x="generate",
                axis_y=[f"variation:{variation}"],
                axis_z={"latency_ms": latency, "ok": False, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "scenario": None,
                "counterfactual_output": "",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # MULTI‑VARIATION ANALYSIS
    # ------------------------------------------------------------
    def generate_many(self, base_text: str, variations: List[str]) -> Dict[str, Any]:
        start = time.time()
        results = []

        try:
            for v in variations:
                results.append(self.generate(base_text, v))

            latency = int((time.time() - start) * 1000)
            self._last_3d = Counterfactual3D(
                axis_x="generate_many",
                axis_y=[f"count:{len(variations)}"],
                axis_z={"latency_ms": latency},
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "base": base_text,
                "results": results,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)
            self._last_3d = Counterfactual3D(
                axis_x="generate_many",
                axis_y=[f"count:{len(variations)}"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "base": base_text,
                "results": results,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
