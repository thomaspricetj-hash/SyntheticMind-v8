from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict, Any
from .symbolic import Expr, Eq, Symbol, Add, Mul, Number, Neg, Pow
import math


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Solver3D:
    """
    3D structural view of a solve operation.

    axis_x: raw equation string
    axis_y: expression node decomposition
    axis_z: metadata (coefficients, discriminant, solution type)
    """
    raw_expr: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[Solver3D] = None


# ============================================================
# INTERNAL 3D BUILDER
# ============================================================

def _build_3d(expr: Expr, var: Symbol, kind: str, coeffs: Dict[str, float], result: Any) -> Solver3D:
    def walk(e: Expr, out: List[str]):
        out.append(type(e).__name__)
        if isinstance(e, Add) or isinstance(e, Mul):
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
        "kind": kind,
        "variable": var.name,
        "coefficients": coeffs,
        "result": result,
        "node_count": len(structure),
    }

    return Solver3D(
        raw_expr=str(expr),
        axis_x=str(expr),
        axis_y=structure,
        axis_z=axis_z,
    )


# ============================================================
# LINEAR COLLECTION
# ============================================================

def _collect_linear(expr: Expr, var: Symbol) -> Tuple[float, float]:
    # returns (a, b) for a*var + b
    if isinstance(expr, Number):
        return 0.0, float(expr.value)
    if isinstance(expr, Symbol):
        if expr.name == var.name:
            return 1.0, 0.0
        return 0.0, 0.0
    if isinstance(expr, Add):
        a1, b1 = _collect_linear(expr.left, var)
        a2, b2 = _collect_linear(expr.right, var)
        return a1 + a2, b1 + b2
    if isinstance(expr, Mul):
        if isinstance(expr.left, Number):
            a, b = _collect_linear(expr.right, var)
            return expr.left.value * a, expr.left.value * b
        if isinstance(expr.right, Number):
            a, b = _collect_linear(expr.left, var)
            return expr.right.value * a, expr.right.value * b
    if isinstance(expr, Neg):
        a, b = _collect_linear(expr.expr, var)
        return -a, -b
    return 0.0, 0.0


def solve_linear(eq: Eq, var: Symbol) -> Optional[float]:
    global _last_3d

    left = Add(eq.left, Neg(eq.right)).simplify()
    a, b = _collect_linear(left, var)

    if a == 0:
        _last_3d = _build_3d(
            left, var, "linear_unsolvable",
            {"a": a, "b": b},
            result=None
        )
        return None

    sol = -b / a

    _last_3d = _build_3d(
        left, var, "linear",
        {"a": a, "b": b},
        result=sol
    )

    return sol


# ============================================================
# QUADRATIC COLLECTION
# ============================================================

def _collect_quadratic(expr: Expr, var: Symbol) -> Tuple[float, float, float]:
    # returns (a, b, c) for a*var^2 + b*var + c
    if isinstance(expr, Number):
        return 0.0, 0.0, float(expr.value)
    if isinstance(expr, Symbol):
        if expr.name == var.name:
            return 0.0, 1.0, 0.0
        return 0.0, 0.0, 0.0
    if isinstance(expr, Pow):
        if isinstance(expr.base, Symbol) and expr.base.name == var.name and isinstance(expr.exp, Number) and expr.exp.value == 2:
            return 1.0, 0.0, 0.0
        return 0.0, 0.0, 0.0
    if isinstance(expr, Add):
        a1, b1, c1 = _collect_quadratic(expr.left, var)
        a2, b2, c2 = _collect_quadratic(expr.right, var)
        return a1 + a2, b1 + b2, c1 + c2
    if isinstance(expr, Mul):
        if isinstance(expr.left, Number):
            a, b, c = _collect_quadratic(expr.right, var)
            k = expr.left.value
            return k * a, k * b, k * c
        if isinstance(expr.right, Number):
            a, b, c = _collect_quadratic(expr.left, var)
            k = expr.right.value
            return k * a, k * b, k * c
    if isinstance(expr, Neg):
        a, b, c = _collect_quadratic(expr.expr, var)
        return -a, -b, -c
    return 0.0, 0.0, 0.0


def solve_quadratic(eq: Eq, var: Symbol) -> Optional[List[float]]:
    global _last_3d

    left = Add(eq.left, Neg(eq.right)).simplify()
    a, b, c = _collect_quadratic(left, var)

    if a == 0:
        _last_3d = _build_3d(
            left, var, "quadratic_not_quadratic",
            {"a": a, "b": b, "c": c},
            result=None
        )
        return None

    disc = b * b - 4 * a * c

    if disc < 0:
        _last_3d = _build_3d(
            left, var, "quadratic_no_real",
            {"a": a, "b": b, "c": c, "discriminant": disc},
            result=[]
        )
        return []

    if disc == 0:
        sol = [(-b) / (2 * a)]
        _last_3d = _build_3d(
            left, var, "quadratic_single",
            {"a": a, "b": b, "c": c, "discriminant": disc},
            result=sol
        )
        return sol

    sqrt_d = math.sqrt(disc)
    sol = [(-b - sqrt_d) / (2 * a), (-b + sqrt_d) / (2 * a)]

    _last_3d = _build_3d(
        left, var, "quadratic_two",
        {"a": a, "b": b, "c": c, "discriminant": disc},
        result=sol
    )

    return sol

