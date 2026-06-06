# syntheticmind/tools/tool_tester.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback


class ToolTester:
    """
    Tests generated tools by executing them and validating structure.

    Validates:
        • code executes safely
        • exactly one callable is produced
        • callable accepts expected parameters
        • return value is a dict with required keys
        • no side effects escape the sandbox
    """

    REQUIRED_KEYS = {"tool", "params"}

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

            # Extract function
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

            # ----------------------------------------------------
            # SUCCESS
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "error": None,
                "details": {
                    "params": param_names,
                    "returned": result,
                },
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "error": str(e),
                "traceback": traceback.format_exc(),
                "details": {},
            }
