from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
from .symbolic import Expr, Number, Symbol, Add, Mul, Pow, Neg


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class Derivative3D:
    """
    3D structural view of a symbolic derivative operation.

    axis_x: raw expression
    axis_y: structural decomposition (node types)
    axis_z: metadata about derivative steps
    """
    raw_expr: Expr
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# INTERNAL: build 3D structure
# ------------------------------------------------------------
def _build_3d(expr: Expr, var: Symbol, steps: List[str]) -> Derivative3D:
    def walk(e: Expr, out: List[str]):
        out.append(type(e).__name__)
        if isinstance(e, (Add, Mul)):
            walk(e.left, out)
            walk(e.right, out)
        elif isinstance(e, Pow):
            walk(e.base, out)
            walk(e.exp, out)
        elif isinstance(e, Neg):
            walk(e.expr, out)

    structure: List[str] = []
    walk(expr, structure)

    axis_z = {
        "variable": var.name,
        "steps": steps,
        "node_count": len(structure),
    }

    return Derivative3D(
        raw_expr=expr,
        axis_x=str(expr),
        axis_y=structure,
        axis_z=axis_z,
    )


# ------------------------------------------------------------
# MAIN DERIVATIVE FUNCTION (3D-AWARE)
# ------------------------------------------------------------
def d(expr: Expr, var: Symbol) -> Expr:
    """
    Computes the symbolic derivative AND attaches a 3D structural
    representation to expr._derivative_3d for orchestrator use.
    """

    steps: List[str] = []

    def _d(e: Expr) -> Expr:
        # Number
        if isinstance(e, Number):
            steps.append(f"d({e}) = 0")
            return Number(0)

        # Symbol
        if isinstance(e, Symbol):
            val = 1 if e.name == var.name else 0
            steps.append(f"d({e}) = {val}")
            return Number(val)

        # Addition
        if isinstance(e, Add):
            steps.append(f"d({e}) = d(left) + d(right)")
            return Add(_d(e.left), _d(e.right)).simplify()

        # Multiplication (product rule)
        if isinstance(e, Mul):
            steps.append(f"d({e}) = d(left)*right + left*d(right)")
            return Add(
                Mul(_d(e.left), e.right),
                Mul(e.left, _d(e.right))
            ).simplify()

        # Power rule (x^n)
        if isinstance(e, Pow):
            if isinstance(e.base, Symbol) and isinstance(e.exp, Number):
                n = e.exp.value
                steps.append(f"d({e}) = {n} * x^{n-1}")
                return Mul(Number(n), Pow(e.base, Number(n - 1))).simplify()

        # Negation
        if isinstance(e, Neg):
            steps.append(f"d({e}) = -d(inner)")
            return Neg(_d(e.expr)).simplify()

        # Default fallback
        steps.append(f"d({e}) = 0 (fallback)")
        return Number(0)

    # Compute derivative
    result = _d(expr)

    # Attach 3D structure to the expression for orchestrator use
    expr._derivative_3d = _build_3d(expr, var, steps)

    return result
