# syntheticmind/strategy/strategy_analyzer.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class StrategyAnalyzer:
    """
    Scores and summarizes candidate plans.
    Provides:
        • structured envelopes
        • multi-factor scoring
        • complexity analysis
        • risk weighting
        • feasibility heuristics
        • safe execution
        • future-proof hooks for TaskGraphPlanner
    """

    # ------------------------------------------------------------
    # MAIN ANALYSIS ENTRYPOINT
    # ------------------------------------------------------------
    def analyze(self, plans: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Returns a structured analysis envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "candidates": [...],
                "best": {...},
                "error": None
            }
        """

        start = time.time()
        scored = []

        try:
            for p in plans:
                scored.append(self._score_plan(p))

            # Sort by score descending
            scored.sort(key=lambda x: x["score"], reverse=True)
            best = scored[0] if scored else None

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "candidates": scored,
                "best": best,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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
