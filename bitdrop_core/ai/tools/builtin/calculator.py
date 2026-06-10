import math
from typing import Any, Dict
from dataclasses import dataclass


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Calc3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SAFE MATH ENVIRONMENT
# ============================================================

_SAFE_MATH_ENV = {
    name: getattr(math, name)
    for name in dir(math)
    if not name.startswith("_")
}

_SAFE_MATH_ENV.update({
    "pi": math.pi,
    "tau": math.tau,
    "e": math.e,
    "inf": math.inf,
    "nan": math.nan,
})

_SAFE_MATH_ENV["__builtins__"] = {}


# ============================================================
# CALCULATOR TOOL — MAX SAFETY + 3D‑MAX
# ============================================================

def calculator_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe, high‑performance calculator for arithmetic and math functions (3D‑MAX Edition).

    Features:
        • precompiled expression for speed
        • expanded safe math environment
        • explicit constants (pi, e, tau, inf, nan)
        • better error messages
        • rejects empty or malicious expressions
        • zero builtins, zero imports, zero I/O
        • 3D‑MAX telemetry
    """

    expr = str(args.get("expression", "")).strip()
    if not expr:
        return {
            "error": "missing expression",
            "_3d": Calc3D(
                axis_x="calculator_tool",
                axis_y=["missing_expr"],
                axis_z={"ok": False},
            ),
        }

    # Forbidden patterns
    forbidden = ["__", "import", "open", "exec", "eval", "os.", "sys."]
    if any(tok in expr for tok in forbidden):
        return {
            "error": "unsafe expression",
            "_3d": Calc3D(
                axis_x="calculator_tool",
                axis_y=["forbidden"],
                axis_z={"expr": expr},
            ),
        }

    try:
        compiled = compile(expr, "<calculator>", "eval")
        value = eval(compiled, _SAFE_MATH_ENV, {})

        return {
            "result": value,
            "_3d": Calc3D(
                axis_x="calculator_tool",
                axis_y=["ok"],
                axis_z={
                    "expr_len": len(expr),
                    "result_type": type(value).__name__,
                },
            ),
        }

    except SyntaxError as e:
        return {
            "error": f"syntax error: {e.msg}",
            "_3d": Calc3D(
                axis_x="calculator_tool",
                axis_y=["syntax_error"],
                axis_z={"msg": e.msg},
            ),
        }

    except Exception as e:
        return {
            "error": f"evaluation failed: {e}",
            "_3d": Calc3D(
                axis_x="calculator_tool",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            ),
        }

