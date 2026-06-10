from typing import Any, Dict
from dataclasses import dataclass
import io
import contextlib


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class PyExec3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# FORBIDDEN PATTERNS
# ============================================================

_FORBIDDEN = [
    "__", "import", "open", "exec", "eval", "os.", "sys.", "subprocess",
    "globals", "locals", "compile", "breakpoint", "input"
]


# ============================================================
# PYTHON EXEC TOOL — MAX SAFETY + 3D‑MAX
# ============================================================

def python_exec_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hardened, sandboxed Python executor (3D‑MAX Edition).

    Features:
        • blocks dangerous patterns (__import__, os, sys, etc.)
        • captures stdout safely
        • returns locals + stdout
        • precompiles code for cleaner errors
        • zero builtins, zero imports, zero I/O
        • structured error messages
        • 3D‑MAX telemetry
    """

    code = str(args.get("code", "")).strip()
    if not code:
        return {
            "error": "missing code",
            "_3d": PyExec3D(
                axis_x="python_exec_tool",
                axis_y=["missing_code"],
                axis_z={"ok": False},
            ),
        }

    # ------------------------------------------------------------
    # SAFETY CHECKS
    # ------------------------------------------------------------
    lowered = code.replace(" ", "").lower()
    for bad in _FORBIDDEN:
        if bad in lowered:
            return {
                "error": f"unsafe code detected: '{bad}'",
                "_3d": PyExec3D(
                    axis_x="python_exec_tool",
                    axis_y=["forbidden"],
                    axis_z={"token": bad},
                ),
            }

    # ------------------------------------------------------------
    # SANDBOX ENVIRONMENT
    # ------------------------------------------------------------
    safe_globals = {"__builtins__": {}}   # no builtins at all
    safe_locals: Dict[str, Any] = {}

    stdout_buffer = io.StringIO()

    try:
        # Precompile for better syntax error reporting
        compiled = compile(code, "<python_exec>", "exec")

        with contextlib.redirect_stdout(stdout_buffer):
            exec(compiled, safe_globals, safe_locals)

        out = {
            "stdout": stdout_buffer.getvalue(),
            "locals": safe_locals,
            "_3d": PyExec3D(
                axis_x="python_exec_tool",
                axis_y=["ok"],
                axis_z={
                    "stdout_len": len(stdout_buffer.getvalue()),
                    "locals_count": len(safe_locals),
                },
            ),
        }
        return out

    except SyntaxError as e:
        return {
            "error": f"syntax error: {e.msg} at line {e.lineno}",
            "_3d": PyExec3D(
                axis_x="python_exec_tool",
                axis_y=["syntax_error"],
                axis_z={"msg": e.msg, "line": e.lineno},
            ),
        }

    except Exception as e:
        return {
            "error": f"exec failed: {e}",
            "_3d": PyExec3D(
                axis_x="python_exec_tool",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            ),
        }


