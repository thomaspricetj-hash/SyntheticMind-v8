# syntheticmind/metamodel/refiner.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from .critic import Critic
from .improver import Improver


class Refiner:
    """
    Multi-pass refinement engine.
    Performs:
        • critique → improve loops
        • structured envelopes
        • latency tracking
        • early exit on failure
        • runaway-loop protection
    """

    def __init__(self):
        self.critic = Critic()
        self.improver = Improver()

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def refine(self, prompt: str, output: str, passes: int = 2) -> Dict[str, Any]:
        """
        Returns a structured refinement envelope:
            {
                "ok": bool,
                "passes": int,
                "latency_ms": int,
                "final_output": str,
                "history": [...],
                "error": str | None
            }
        """

        start = time.time()
        history = []
        current = output

        try:
            for i in range(passes):
                pass_start = time.time()

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
                # 3. RUNAWAY LOOP PROTECTION
                # ------------------------------------------------
                if improved_text.strip() == current.strip():
                    # No change → stop early
                    return {
                        "ok": True,
                        "passes": i + 1,
                        "latency_ms": int((time.time() - start) * 1000),
                        "final_output": current,
                        "history": history,
                        "notes": "early exit: no further improvement detected",
                        "error": None,
                    }

                current = improved_text

            # ----------------------------------------------------
            # SUCCESSFUL COMPLETION
            # ----------------------------------------------------
            return {
                "ok": True,
                "passes": passes,
                "latency_ms": int((time.time() - start) * 1000),
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
        return {
            "ok": False,
            "passes": len(history) // 2,
            "latency_ms": int((time.time() - start) * 1000),
            "final_output": "",
            "history": history,
            "error": error,
            "traceback": tb,
        }
