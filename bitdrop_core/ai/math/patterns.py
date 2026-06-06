from __future__ import annotations
from typing import Callable, Optional
from .symbolic import Expr, Add, Mul, Pow, Number, Symbol, Neg


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


def rewrite_once(expr: Expr) -> Expr:
    for rule in RULES:
        out = rule.try_apply(expr)
        if out is not None:
            return out
    return expr
