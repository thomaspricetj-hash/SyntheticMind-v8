from __future__ import annotations
from dataclasses import dataclass
from typing import Union, List, Dict

NumberT = Union[int, float]


class Expr:
    def simplify(self) -> "Expr":
        return self

    def __add__(self, other):
        return Add(self, to_expr(other)).simplify()

    def __radd__(self, other):
        return Add(to_expr(other), self).simplify()

    def __sub__(self, other):
        return Add(self, Neg(to_expr(other))).simplify()

    def __rsub__(self, other):
        return Add(to_expr(other), Neg(self)).simplify()

    def __mul__(self, other):
        return Mul(self, to_expr(other)).simplify()

    def __rmul__(self, other):
        return Mul(to_expr(other), self).simplify()

    def __truediv__(self, other):
        return Mul(self, Pow(to_expr(other), Number(-1))).simplify()

    def __rtruediv__(self, other):
        return Mul(to_expr(other), Pow(self, Number(-1))).simplify()

    def __pow__(self, power, modulo=None):
        return Pow(self, to_expr(power)).simplify()

    def __neg__(self):
        return Neg(self).simplify()

    def __repr__(self):
        return self.__str__()


@dataclass
class Number(Expr):
    value: NumberT

    def simplify(self) -> Expr:
        return self

    def __str__(self):
        return str(self.value)


@dataclass
class Symbol(Expr):
    name: str

    def __str__(self):
        return self.name


@dataclass
class Add(Expr):
    left: Expr
    right: Expr

    def simplify(self) -> Expr:
        l = self.left.simplify()
        r = self.right.simplify()

        if isinstance(l, Number) and isinstance(r, Number):
            return Number(l.value + r.value)

        if isinstance(l, Number) and l.value == 0:
            return r
        if isinstance(r, Number) and r.value == 0:
            return l

        return Add(l, r)

    def __str__(self):
        return f"({self.left} + {self.right})"


@dataclass
class Mul(Expr):
    left: Expr
    right: Expr

    def simplify(self) -> Expr:
        l = self.left.simplify()
        r = self.right.simplify()

        if isinstance(l, Number) and isinstance(r, Number):
            return Number(l.value * r.value)

        if (isinstance(l, Number) and l.value == 0) or (isinstance(r, Number) and r.value == 0):
            return Number(0)

        if isinstance(l, Number) and l.value == 1:
            return r
        if isinstance(r, Number) and r.value == 1:
            return l

        return Mul(l, r)

    def __str__(self):
        return f"({self.left} * {self.right})"


@dataclass
class Pow(Expr):
    base: Expr
    exp: Expr

    def simplify(self) -> Expr:
        b = self.base.simplify()
        e = self.exp.simplify()

        if isinstance(b, Number) and isinstance(e, Number):
            return Number(b.value ** e.value)

        if isinstance(e, Number) and e.value == 1:
            return b
        if isinstance(e, Number) and e.value == 0:
            return Number(1)

        return Pow(b, e)

    def __str__(self):
        return f"({self.base} ^ {self.exp})"


@dataclass
class Neg(Expr):
    expr: Expr

    def simplify(self) -> Expr:
        e = self.expr.simplify()
        if isinstance(e, Number):
            return Number(-e.value)
        return Neg(e)

    def __str__(self):
        return f"-({self.expr})"


@dataclass
class Eq(Expr):
    left: Expr
    right: Expr

    def __str__(self):
        return f"{self.left} = {self.right}"


def to_expr(x: Union[Expr, NumberT, str]) -> Expr:
    if isinstance(x, Expr):
        return x
    if isinstance(x, (int, float)):
        return Number(x)
    if isinstance(x, str):
        return Symbol(x)
    raise TypeError(f"Cannot convert {x!r} to Expr")


def symbols(*names: str) -> List[Symbol]:
    return [Symbol(n) for n in names]


def substitute(expr: Expr, mapping: Dict[str, Expr]) -> Expr:
    if isinstance(expr, Symbol):
        return mapping.get(expr.name, expr)
    if isinstance(expr, Number):
        return expr
    if isinstance(expr, Add):
        return Add(substitute(expr.left, mapping), substitute(expr.right, mapping)).simplify()
    if isinstance(expr, Mul):
        return Mul(substitute(expr.left, mapping), substitute(expr.right, mapping)).simplify()
    if isinstance(expr, Pow):
        return Pow(substitute(expr.base, mapping), substitute(expr.exp, mapping)).simplify()
    if isinstance(expr, Neg):
        return Neg(substitute(expr.expr, mapping)).simplify()
    if isinstance(expr, Eq):
        return Eq(substitute(expr.left, mapping), substitute(expr.right, mapping))
    return expr
