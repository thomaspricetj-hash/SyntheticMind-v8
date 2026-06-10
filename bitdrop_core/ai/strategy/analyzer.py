# syntheticmind/strategy/strategy_analyzer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Strategy3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# STRATEGY ANALYZER — MAX SPEED + 3D‑MAX
# ============================================================

class StrategyAnalyzer:
    """
    Scores and summarizes candidate plans (3D‑MAX Edition).

    Provides:
        • structured envelopes
        • multi-factor scoring
        • complexity analysis
        • risk weighting
        • feasibility heuristics
        • safe execution
        • 3D‑MAX introspection
        • future-proof hooks for TaskGraphPlanner
    """

    def __init__(self):
        self._last_3d: Optional[Strategy3D] = None

    # ------------------------------------------------------------
    # MAIN ANALYSIS ENTRYPOINT
    # ------------------------------------------------------------
    def analyze(self, plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        start = time.time()
        scored: List[Dict[str, Any]] = []

        try:
            for p in plans:
                scored.append(self._score_plan(p))

            scored.sort(key=lambda x: x["score"], reverse=True)
            best = scored[0] if scored else None

            latency = int((time.time() - start) * 1000)

            self._last_3d = Strategy3D(
                axis_x="analyze",
                axis_y=[f"plans:{len(plans)}"],
                axis_z={
                    "latency_ms": latency,
                    "best_score": best["score"] if best else None,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "candidates": scored,
                "best": best,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = Strategy3D(
                axis_x="analyze",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "candidates": scored,
                "best": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL: SCORE A SINGLE PLAN
    # ------------------------------------------------------------
    def _score_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-factor scoring:
            • complexity penalty (more steps → lower score)
            • risk penalty
            • feasibility bonus
            • structure bonus
        """

        steps = plan.get("steps", [])
        risk = float(plan.get("risk", 0.5))
        feasibility = float(plan.get("feasibility", 0.5))
        structure = float(plan.get("structure", 0.5))

        # Complexity penalty
        complexity_penalty = len(steps) * 0.05

        # Risk penalty
        risk_penalty = risk * 0.3

        # Feasibility bonus
        feasibility_bonus = feasibility * 0.2

        # Structure bonus
        structure_bonus = structure * 0.1

        # Final score
        score = 1.0 - complexity_penalty - risk_penalty + feasibility_bonus + structure_bonus
        score = max(0.0, min(1.0, score))

        # 3D‑MAX telemetry for per‑plan scoring
        self._last_3d = Strategy3D(
            axis_x="_score_plan",
            axis_y=[f"steps:{len(steps)}", f"risk:{risk}"],
            axis_z={
                "score": score,
                "complexity_penalty": complexity_penalty,
                "risk_penalty": risk_penalty,
                "feasibility_bonus": feasibility_bonus,
                "structure_bonus": structure_bonus,
            },
        )

        return {
            "plan": plan,
            "score": score,
            "details": {
                "complexity_penalty": complexity_penalty,
                "risk_penalty": risk_penalty,
                "feasibility_bonus": feasibility_bonus,
                "structure_bonus": structure_bonus,
            },
        }

