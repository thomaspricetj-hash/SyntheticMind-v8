# syntheticmind/tools/python_tool.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import io
import time
import traceback
import contextlib


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class PyTool3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# PYTHON TOOL — MAX SANDBOX + 3D‑MAX
# ============================================================

class PythonTool:
    """
    Safe(ish) Python execution sandbox (3D‑MAX Edition).
    Executes code and returns stdout + structured metadata.

    Features:
        • isolated namespace
        • stdout capture
        • stderr capture
        • structured envelopes
        • latency measurement
        • safe builtins (empty by default)
        • 3D‑MAX telemetry
    """

    SAFE_GLOBALS = {
        "__builtins__": {}
    }

    def __init__(self):
        self._last_3d: Optional[PyTool3D] = None

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

            latency = int((time.time() - start) * 1000)

            self._last_3d = PyTool3D(
                axis_x="run",
                axis_y=["ok"],
                axis_z={
                    "latency_ms": latency,
                    "stdout_len": len(stdout_buffer.getvalue()),
                    "stderr_len": len(stderr_buffer.getvalue()),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = PyTool3D(
                axis_x="run",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": latency,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "stdout": stdout_buffer.getvalue(),
                "stderr": stderr_buffer.getvalue(),
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


