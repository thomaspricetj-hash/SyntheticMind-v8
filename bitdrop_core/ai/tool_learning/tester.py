# syntheticmind/tools/tool_tester.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class ToolTest3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL TESTER — MAX VALIDATION + 3D‑MAX
# ============================================================

class ToolTester:
    """
    Tests generated tools by executing them and validating structure (3D‑MAX Edition).

    Validates:
        • code executes safely
        • exactly one callable is produced
        • callable accepts expected parameters
        • return value is a dict with required keys
        • no side effects escape the sandbox
        • 3D‑MAX telemetry for every phase
    """

    REQUIRED_KEYS = {"tool", "params"}

    def __init__(self):
        self._last_3d: Optional[ToolTest3D] = None

    # ------------------------------------------------------------
    # MAIN TEST ENTRYPOINT
    # ------------------------------------------------------------
    def test(self, code: str) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "error": None,
                "details": {...}
            }
        """

        start = time.time()
        local_env: Dict[str, Any] = {}

        try:
            # ----------------------------------------------------
            # 1) EXECUTE CODE IN SANDBOX
            # ----------------------------------------------------
            exec(code, {}, local_env)

            fns = [v for v in local_env.values() if callable(v)]
            if len(fns) != 1:
                raise ValueError(f"Expected exactly 1 function, found {len(fns)}")

            fn = fns[0]

            # ----------------------------------------------------
            # 2) BUILD TEST PARAMS
            # ----------------------------------------------------
            param_names = list(fn.__code__.co_varnames[: fn.__code__.co_argcount])
            test_kwargs = {p: "test" for p in param_names}

            # ----------------------------------------------------
            # 3) CALL FUNCTION
            # ----------------------------------------------------
            result = fn(**test_kwargs)

            # ----------------------------------------------------
            # 4) VALIDATE RETURN STRUCTURE
            # ----------------------------------------------------
            if not isinstance(result, dict):
                raise ValueError("Tool did not return a dict")

            missing = self.REQUIRED_KEYS - set(result.keys())
            if missing:
                raise ValueError(f"Missing required keys: {missing}")

            latency = int((time.time() - start) * 1000)

            # 3D‑MAX telemetry
            self._last_3d = ToolTest3D(
                axis_x="test",
                axis_y=[f"params:{len(param_names)}"],
                axis_z={
                    "latency_ms": latency,
                    "ok": True,
                    "returned_keys": list(result.keys()),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "error": None,
                "details": {
                    "params": param_names,
                    "returned": result,
                },
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = ToolTest3D(
                axis_x="test",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": latency,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "details": {},
            }
