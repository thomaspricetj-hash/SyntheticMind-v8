from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Rollout3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SIMULATION ROLLOUT — MAX SPEED + 3D‑MAX
# ============================================================

class SimulationRollout:
    """
    Evaluates simulated outcomes (3D‑MAX Edition).
    Provides:
        • structured scoring envelopes
        • severity classification
        • anomaly detection
        • per-step scoring
        • latency measurement
        • future-proof rollout analytics
        • 3D‑MAX introspection for every rollout
    """

    def __init__(self):
        self._last_3d: Rollout3D | None = None

    # ------------------------------------------------------------
    # MAIN SCORING FUNCTION
    # ------------------------------------------------------------
    def score(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        start = time.time()
        step_scores = []

        try:
            successes = 0
            errors = 0
            anomalies = 0

            for i, r in enumerate(results):
                step_score = self._score_step(r)
                step_scores.append(step_score)

                status = step_score["status"]
                if status == "success":
                    successes += 1
                elif status == "error":
                    errors += 1
                elif status == "anomaly":
                    anomalies += 1

            total = len(results)
            success_rate = successes / total if total > 0 else 0.0

            latency = int((time.time() - start) * 1000)
            self._last_3d = Rollout3D(
                axis_x="score",
                axis_y=[f"steps:{total}", f"successes:{successes}", f"errors:{errors}", f"anomalies:{anomalies}"],
                axis_z={
                    "latency_ms": latency,
                    "success_rate": success_rate,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
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
            latency = int((time.time() - start) * 1000)
            self._last_3d = Rollout3D(
                axis_x="score",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
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

        # Structured simulation envelope
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


