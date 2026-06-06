# syntheticmind/tools/python_tool.py

from __future__ import annotations
from typing import Dict, Any
import io
import time
import traceback
import contextlib


class PythonTool:
    """
    Safe(ish) Python execution sandbox.
    Executes code and returns stdout + structured metadata.

    Features:
        • isolated namespace
        • stdout capture
        • stderr capture
        • structured envelopes
        • latency measurement
        • safe builtins (empty by default)
    """

    SAFE_GLOBALS = {
        "__builtins__": {}
    }

    # ------------------------------------------------------------
    # MAIN EXECUTION ENTRYPOINT
    # ------------------------------------------------------------
    def run(self, code: str) -> Dict[str, Any]:
        """
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "stdout": str,
                "stderr": str,
                "error": None
            }
        """

        start = time.time()
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buffer), \
                 contextlib.redirect_stderr(stderr_buffer):

                exec(code, self.SAFE_GLOBALS, {})

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

