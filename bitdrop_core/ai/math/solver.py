from __future__ import annotations
from typing import Optional, Tuple, List
from .symbolic import Expr, Eq, Symbol, Add, Mul, Number, Neg, Pow


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
    # solve a*var + b = 0 form
    left = Add(eq.left, Neg(eq.right)).simplify()
    a, b = _collect_linear(left, var)
    if a == 0:
        return None
    return -b / a


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
        # handle k * x^2, k * x, k * const
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
    # solve a*var^2 + b*var + c = 0
    left = Add(eq.left, Neg(eq.right)).simplify()
    a, b, c = _collect_quadratic(left, var)
    if a == 0:
        return None
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    if disc == 0:
        return [(-b) / (2 * a)]
    import math
    sqrt_d = math.sqrt(disc)
    return [(-b - sqrt_d) / (2 * a), (-b + sqrt_d) / (2 * a)]
