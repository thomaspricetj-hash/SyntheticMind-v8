# syntheticmind/metamodel/simulation_rollout.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback


class SimulationRollout:
    """
    Evaluates simulated outcomes.
    Provides:
        • structured scoring envelopes
        • severity classification
        • anomaly detection
        • per-step scoring
        • latency measurement
        • future-proof rollout analytics
    """

    # ------------------------------------------------------------
    # MAIN SCORING FUNCTION
    # ------------------------------------------------------------
    def score(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        results: list of simulation step outputs
        Returns a structured rollout evaluation:
            {
                "ok": bool,
                "latency_ms": int,
                "summary": {...},
                "steps": [...],
                "error": None
            }
        """

        start = time.time()
        step_scores = []

        try:
            successes = 0
            errors = 0
            anomalies = 0

            for i, r in enumerate(results):
                step_score = self._score_step(r)
                step_scores.append(step_score)

                if step_score["status"] == "success":
                    successes += 1
                elif step_score["status"] == "error":
                    errors += 1
                elif step_score["status"] == "anomaly":
                    anomalies += 1

            total = len(results)
            success_rate = successes / total if total > 0 else 0.0

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "summary": {
                    "total_steps": total,
                    "successes": successes,
                    "errors": errors,
                    "anomalies": anomalies,
                    "success_rate": success_rate,
                },
                "steps": step_scores,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "summary": {},
                "steps": step_scores,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # INTERNAL: SCORE A SINGLE STEP
    # ------------------------------------------------------------
    def _score_step(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifies a single simulation step:
            • success
            • error
            • anomaly
        """

        # Hard error
        if isinstance(result, dict) and result.get("error"):
            return {
                "status": "error",
                "detail": result,
            }

        # Structured simulation envelope from SimulationEngine
        if isinstance(result, dict) and "ok" in result:
            if result["ok"]:
                return {
                    "status": "success",
                    "detail": result,
                }
            else:
                return {
                    "status": "error",
                    "detail": result,
                }

        # Unexpected structure → anomaly
        return {
            "status": "anomaly",
            "detail": result,
        }

