from __future__ import annotations
from .symbolic import Expr, Number, Symbol, Add, Mul, Pow, Neg


def d(expr: Expr, var: Symbol) -> Expr:
    if isinstance(expr, Number):
        return Number(0)
    if isinstance(expr, Symbol):
        return Number(1 if expr.name == var.name else 0)
    if isinstance(expr, Add):
        return Add(d(expr.left, var), d(expr.right, var)).simplify()
    if isinstance(expr, Mul):
        # product rule
        return Add(
            Mul(d(expr.left, var), expr.right),
            Mul(expr.left, d(expr.right, var))
        ).simplify()
    if isinstance(expr, Pow):
        # only handle x^n where n is number
        if isinstance(expr.base, Symbol) and isinstance(expr.exp, Number):
            n = expr.exp.value
            return Mul(Number(n), Pow(expr.base, Number(n - 1))).simplify()
    if isinstance(expr, Neg):
        return Neg(d(expr.expr, var)).simplify()
    return Number(0)
