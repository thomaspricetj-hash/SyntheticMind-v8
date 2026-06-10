from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .symbolic import Expr, Symbol, Number, Add, Mul, Pow
from .solver import solve_quadratic


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class CAS3D:
    """
    3D structural view of a CAS operation.

    axis_x: raw expression string
    axis_y: expression tree node types
    axis_z: metadata (op, before/after, coefficients, roots, etc.)
    """
    raw_expr: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[CAS3D] = None


# ============================================================
# INTERNAL 3D BUILDER
# ============================================================

def _build_3d(before: Expr | str, after: Any, op: str, extra: Dict[str, Any] | None = None) -> CAS3D:
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
    if isinstance(before, Expr):
        walk(before, structure)

    axis_z = {
        "op": op,
        "before": str(before),
        "after": str(after),
        "node_count": len(structure),
    }
    if extra:
        axis_z.update(extra)

    return CAS3D(
        raw_expr=str(before),
        axis_x=str(before),
        axis_y=structure,
        axis_z=axis_z,
    )


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
    global _last_3d
    out = _integrate(expr, var)
    _last_3d = _build_3d(expr, out, "integrate", extra={"var": var.name})
    return out


# ============================================================
# LIMITS (SMALL SET)
# ============================================================

@dataclass
class LimitResult:
    value: Optional[float]
    description: str


def limit(expr_str: str, var_name: str, point: float) -> LimitResult:
    global _last_3d

    s = expr_str.replace(" ", "").lower()

    # classic special case
    if s == "sin(x)/x" and var_name == "x" and abs(point) < 1e-12:
        res = LimitResult(1.0, "lim x→0 sin(x)/x = 1")
        _last_3d = CAS3D(
            raw_expr=expr_str,
            axis_x=expr_str,
            axis_y=["Limit"],
            axis_z={
                "op": "limit",
                "point": point,
                "var": var_name,
                "result": res.description,
            },
        )
        return res

    res = LimitResult(None, "limit not implemented")
    _last_3d = CAS3D(
        raw_expr=expr_str,
        axis_x=expr_str,
        axis_y=["Limit"],
        axis_z={
            "op": "limit",
            "point": point,
            "var": var_name,
            "result": res.description,
        },
    )
    return res


# ============================================================
# QUADRATIC FACTORING
# ============================================================

def factor_quadratic(expr: Expr, var: Symbol) -> Optional[Expr]:
    global _last_3d

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
            _last_3d = _build_3d(expr, None, "factor_quadratic_fail")
            return None

    # solve roots
    from .symbolic import Eq
    eq = Eq(expr, Number(0.0))
    roots = solve_quadratic(eq, var)

    if not roots:
        _last_3d = _build_3d(expr, None, "factor_quadratic_no_roots")
        return None

    from .symbolic import Add as SAdd, Mul as SMul, Number as SNumber

    if len(roots) == 1:
        r = roots[0]
        out = SMul(SNumber(a), SAdd(var, SNumber(-r)))
        _last_3d = _build_3d(expr, out, "factor_quadratic_single", extra={"roots": roots})
        return out

    r1, r2 = roots
    out = SMul(SNumber(a), SMul(SAdd(var, SNumber(-r1)), SAdd(var, SNumber(-r2))))
    _last_3d = _build_3d(expr, out, "factor_quadratic_two", extra={"roots": roots})
    return out


