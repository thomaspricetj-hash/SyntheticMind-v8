from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .symbolic import Expr, Symbol, Number, Add, Mul, Pow
from .solver import solve_quadratic


# ============================================================
# BASIC SYMBOLIC INTEGRATION
# ============================================================

def _is_const(expr: Expr, var: Symbol) -> bool:
    if isinstance(expr, Number):
        return True
    if isinstance(expr, Symbol):
        return expr.name != var.name
    if isinstance(expr, Add):
        return _is_const(expr.left, var) and _is_const(expr.right, var)
    if isinstance(expr, Mul):
        return _is_const(expr.left, var) and _is_const(expr.right, var)
    if isinstance(expr, Pow):
        return _is_const(expr.base, var) and _is_const(expr.exp, var)
    return False


def _integrate(expr: Expr, var: Symbol) -> Optional[Expr]:
    # ∫ c dx = c x
    if isinstance(expr, Number):
        return Mul(expr, var)

    # ∫ x dx = x^2 / 2
    if isinstance(expr, Symbol) and expr.name == var.name:
        return Mul(Number(0.5), Pow(var, Number(2.0)))

    # ∫ x^n dx = x^(n+1)/(n+1)
    if isinstance(expr, Pow) and isinstance(expr.base, Symbol) and expr.base.name == var.name:
        if isinstance(expr.exp, Number):
            n = expr.exp.value
            if n != -1:
                return Mul(
                    Number(1.0 / (n + 1.0)),
                    Pow(var, Number(n + 1.0)),
                )

    # ∫ c * f dx
    if isinstance(expr, Mul):
        if _is_const(expr.left, var):
            inner = _integrate(expr.right, var)
            if inner:
                return Mul(expr.left, inner)
        if _is_const(expr.right, var):
            inner = _integrate(expr.left, var)
            if inner:
                return Mul(expr.right, inner)

    # ∫ (f + g) dx
    if isinstance(expr, Add):
        left = _integrate(expr.left, var)
        right = _integrate(expr.right, var)
        if left and right:
            return Add(left, right)

    return None


def integrate(expr: Expr, var: Symbol) -> Optional[Expr]:
    return _integrate(expr, var)


# ============================================================
# LIMITS (SMALL SET)
# ============================================================

@dataclass
class LimitResult:
    value: Optional[float]
    description: str


def limit(expr_str: str, var_name: str, point: float) -> LimitResult:
    s = expr_str.replace(" ", "").lower()

    # classic special case
    if s == "sin(x)/x" and var_name == "x" and abs(point) < 1e-12:
        return LimitResult(1.0, "lim x→0 sin(x)/x = 1")

    return LimitResult(None, "limit not implemented")


# ============================================================
# QUADRATIC FACTORING
# ============================================================

def factor_quadratic(expr: Expr, var: Symbol) -> Optional[Expr]:
    # flatten Add tree
    terms = []

    def flatten(e: Expr):
        if isinstance(e, Add):
            flatten(e.left)
            flatten(e.right)
        else:
            terms.append(e)

    flatten(expr)

    a = 0.0
    b = 0.0
    c = 0.0

    def collect(term: Expr):
        nonlocal a, b, c

        # a*x^2
        if isinstance(term, Pow) and isinstance(term.base, Symbol) and term.base.name == var.name:
            if isinstance(term.exp, Number) and term.exp.value == 2.0:
                a += 1.0
                return True

        if isinstance(term, Mul):
            # c * x^2
            if isinstance(term.left, Number) and isinstance(term.right, Pow):
                if isinstance(term.right.base, Symbol) and term.right.base.name == var.name:
                    if isinstance(term.right.exp, Number) and term.right.exp.value == 2.0:
                        a += term.left.value
                        return True

            # c * x
            if isinstance(term.left, Number) and isinstance(term.right, Symbol) and term.right.name == var.name:
                b += term.left.value
                return True

        # x
        if isinstance(term, Symbol) and term.name == var.name:
            b += 1.0
            return True

        # constant
        if isinstance(term, Number):
            c += term.value
            return True

        return False

    for t in terms:
        if not collect(t):
            return None

    # solve roots
    from .symbolic import Eq
    eq = Eq(expr, Number(0.0))
    roots = solve_quadratic(eq, var)
    if not roots:
        return None

    from .symbolic import Add as SAdd, Mul as SMul, Number as SNumber

    if len(roots) == 1:
        r = roots[0]
        return SMul(SNumber(a), SAdd(var, SNumber(-r)))

    r1, r2 = roots
    return SMul(SNumber(a), SMul(SAdd(var, SNumber(-r1)), SAdd(var, SNumber(-r2))))

