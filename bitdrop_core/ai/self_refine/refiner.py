from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import time
import traceback

from .critic import Critic
from .improver import Improver


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Refiner3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# REFINER — MAX SPEED + 3D‑MAX
# ============================================================

class Refiner:
    """
    Multi-pass refinement engine (3D‑MAX Edition).
    Performs:
        • critique → improve loops
        • structured envelopes
        • latency tracking
        • early exit on no-change
        • safe failure handling
        • 3D‑MAX introspection for every refinement cycle
    """

    def __init__(self):
        self.critic = Critic()
        self.improver = Improver()
        self._last_3d: Refiner3D | None = None

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def refine(self, prompt: str, output: str, passes: int = 2) -> Dict[str, Any]:
        start = time.time()
        history: List[Dict[str, Any]] = []
        current = output

        try:
            for i in range(passes):
                # ------------------------------------------------
                # 1. CRITIQUE
                # ------------------------------------------------
                critique_env = self.critic.critique(prompt, current)
                history.append({"step": "critique", "result": critique_env})

                if not critique_env.get("ok"):
                    return self._fail(
                        start,
                        history,
                        f"Critique failed on pass {i+1}: {critique_env.get('error')}"
                    )

                critique_text = critique_env.get("critique", "")

                # ------------------------------------------------
                # 2. IMPROVE
                # ------------------------------------------------
                improve_env = self.improver.improve(prompt, current, critique_text)
                history.append({"step": "improve", "result": improve_env})

                if not improve_env.get("ok"):
                    return self._fail(
                        start,
                        history,
                        f"Improvement failed on pass {i+1}: {improve_env.get('error')}"
                    )

                improved_text = improve_env.get("improved", "")

                # ------------------------------------------------
                # 3. EARLY EXIT (no change)
                # ------------------------------------------------
                if improved_text.strip() == current.strip():
                    latency = int((time.time() - start) * 1000)
                    self._last_3d = Refiner3D(
                        axis_x="refine",
                        axis_y=[f"early_exit_pass:{i+1}"],
                        axis_z={
                            "latency_ms": latency,
                            "history_len": len(history),
                            "unchanged": True,
                        },
                    )
                    return {
                        "ok": True,
                        "passes": i + 1,
                        "latency_ms": latency,
                        "final_output": current,
                        "history": history,
                        "notes": "early exit: no further improvement detected",
                        "error": None,
                    }

                current = improved_text

            # ----------------------------------------------------
            # SUCCESSFUL COMPLETION
            # ----------------------------------------------------
            latency = int((time.time() - start) * 1000)
            self._last_3d = Refiner3D(
                axis_x="refine",
                axis_y=[f"full_passes:{passes}"],
                axis_z={
                    "latency_ms": latency,
                    "history_len": len(history),
                    "unchanged": False,
                },
            )
            return {
                "ok": True,
                "passes": passes,
                "latency_ms": latency,
                "final_output": current,
                "history": history,
                "error": None,
            }

        except Exception as e:
            return self._fail(start, history, str(e), traceback.format_exc())

    # ------------------------------------------------------------
    # INTERNAL FAILURE HANDLER
    # ------------------------------------------------------------
    def _fail(self, start, history, error, tb=None) -> Dict[str, Any]:
        latency = int((time.time() - start) * 1000)
        self._last_3d = Refiner3D(
            axis_x="refine",
            axis_y=["exception"],
            axis_z={
                "latency_ms": latency,
                "history_len": len(history),
                "error": error,
            },
        )
        return {
            "ok": False,
            "passes": len(history) // 2,
            "latency_ms": latency,
            "final_output": "",
            "history": history,
            "error": error,
            "traceback": tb,
        }

