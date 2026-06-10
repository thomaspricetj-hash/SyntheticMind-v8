from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, Dict, Any, List
from .symbolic import Expr, Add, Mul, Pow, Number, Symbol, Neg


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class PatternRewrite3D:
    """
    3D structural view of a single rewrite attempt.

    axis_x: raw expression string
    axis_y: expression node decomposition
    axis_z: metadata (matched rule, applied, before/after)
    """
    raw_expr: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# INTERNAL 3D BUILDER
# ============================================================

def _build_3d(expr: Expr, rule_name: Optional[str], before: Expr, after: Expr) -> PatternRewrite3D:
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
        "matched_rule": rule_name,
        "applied": rule_name is not None,
        "before": str(before),
        "after": str(after),
        "node_count": len(structure),
    }

    return PatternRewrite3D(
        raw_expr=str(expr),
        axis_x=str(expr),
        axis_y=structure,
        axis_z=axis_z,
    )


# ============================================================
# PATTERN RULES
# ============================================================

class PatternRule:
    def __init__(self, name: str, match: Callable[[Expr], bool], apply: Callable[[Expr], Expr]):
        self.name = name
        self.match = match
        self.apply = apply

    def try_apply(self, expr: Expr) -> Optional[Expr]:
        if self.match(expr):
            return self.apply(expr)
        return None


def is_add_zero(expr: Expr) -> bool:
    return isinstance(expr, Add) and (
        isinstance(expr.left, Number) and expr.left.value == 0
        or isinstance(expr.right, Number) and expr.right.value == 0
    )


def apply_add_zero(expr: Add) -> Expr:
    if isinstance(expr.left, Number) and expr.left.value == 0:
        return expr.right
    if isinstance(expr.right, Number) and expr.right.value == 0:
        return expr.left
    return expr


def is_mul_one(expr: Expr) -> bool:
    return isinstance(expr, Mul) and (
        isinstance(expr.left, Number) and expr.left.value == 1
        or isinstance(expr.right, Number) and expr.right.value == 1
    )


def apply_mul_one(expr: Mul) -> Expr:
    if isinstance(expr.left, Number) and expr.left.value == 1:
        return expr.right
    if isinstance(expr.right, Number) and expr.right.value == 1:
        return expr.left
    return expr


def is_mul_zero(expr: Expr) -> bool:
    return isinstance(expr, Mul) and (
        isinstance(expr.left, Number) and expr.left.value == 0
        or isinstance(expr.right, Number) and expr.right.value == 0
    )


def apply_mul_zero(expr: Mul) -> Expr:
    return Number(0)


def is_pow_one(expr: Expr) -> bool:
    return isinstance(expr, Pow) and isinstance(expr.exp, Number) and expr.exp.value == 1


def apply_pow_one(expr: Pow) -> Expr:
    return expr.base


def is_pow_zero(expr: Expr) -> bool:
    return isinstance(expr, Pow) and isinstance(expr.exp, Number) and expr.exp.value == 0


def apply_pow_zero(expr: Pow) -> Expr:
    return Number(1)


RULES = [
    PatternRule("add_zero", is_add_zero, apply_add_zero),
    PatternRule("mul_one", is_mul_one, apply_mul_one),
    PatternRule("mul_zero", is_mul_zero, apply_mul_zero),
    PatternRule("pow_one", is_pow_one, apply_pow_one),
    PatternRule("pow_zero", is_pow_zero, apply_pow_zero),
]


# ============================================================
# MAIN REWRITE FUNCTION (3D‑MAX)
# ============================================================

_last_3d: Optional[PatternRewrite3D] = None


def rewrite_once(expr: Expr) -> Expr:
    """
    Applies at most one rewrite rule.
    Stores a 3D structural envelope in `_last_3d`.
    """

    global _last_3d
    before = expr

    for rule in RULES:
        out = rule.try_apply(expr)
        if out is not None:
            _last_3d = _build_3d(expr, rule.name, before, out)
            return out

    # No rule matched
    _last_3d = _build_3d(expr, None, before, expr)
    return expr

