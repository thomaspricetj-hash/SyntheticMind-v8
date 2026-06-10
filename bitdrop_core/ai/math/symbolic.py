from __future__ import annotations
from dataclasses import dataclass
from typing import Union, List, Dict, Any

NumberT = Union[int, float]


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Symbolic3D:
    raw_expr: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Symbolic3D | None = None


def _build_3d(before: "Expr", after: "Expr", op: str) -> Symbolic3D:
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
    walk(before, structure)

    return Symbolic3D(
        raw_expr=str(before),
        axis_x=str(before),
        axis_y=structure,
        axis_z={
            "op": op,
            "before": str(before),
            "after": str(after),
            "node_count": len(structure),
        },
    )


# ============================================================
# BASE CLASS
# ============================================================

class Expr:
    def simplify(self) -> "Expr":
        return self

    def __add__(self, other):
        global _last_3d
        out = Add(self, to_expr(other)).simplify()
        _last_3d = _build_3d(self, out, "add")
        return out

    def __radd__(self, other):
        global _last_3d
        out = Add(to_expr(other), self).simplify()
        _last_3d = _build_3d(self, out, "radd")
        return out

    def __sub__(self, other):
        global _last_3d
        out = Add(self, Neg(to_expr(other))).simplify()
        _last_3d = _build_3d(self, out, "sub")
        return out

    def __rsub__(self, other):
        global _last_3d
        out = Add(to_expr(other), Neg(self)).simplify()
        _last_3d = _build_3d(self, out, "rsub")
        return out

    def __mul__(self, other):
        global _last_3d
        out = Mul(self, to_expr(other)).simplify()
        _last_3d = _build_3d(self, out, "mul")
        return out

    def __rmul__(self, other):
        global _last_3d
        out = Mul(to_expr(other), self).simplify()
        _last_3d = _build_3d(self, out, "rmul")
        return out

    def __truediv__(self, other):
        global _last_3d
        out = Mul(self, Pow(to_expr(other), Number(-1))).simplify()
        _last_3d = _build_3d(self, out, "div")
        return out

    def __rtruediv__(self, other):
        global _last_3d
        out = Mul(to_expr(other), Pow(self, Number(-1))).simplify()
        _last_3d = _build_3d(self, out, "rdiv")
        return out

    def __pow__(self, power, modulo=None):
        global _last_3d
        out = Pow(self, to_expr(power)).simplify()
        _last_3d = _build_3d(self, out, "pow")
        return out

    def __neg__(self):
        global _last_3d
        out = Neg(self).simplify()
        _last_3d = _build_3d(self, out, "neg")
        return out

    def __repr__(self):
        return self.__str__()


# ============================================================
# NUMBER
# ============================================================

@dataclass
class Number(Expr):
    value: NumberT

    def simplify(self) -> Expr:
        return self

    def __str__(self):
        return str(self.value)


# ============================================================
# SYMBOL
# ============================================================

@dataclass
class Symbol(Expr):
    name: str

    def __str__(self):
        return self.name


# ============================================================
# ADD
# ============================================================

@dataclass
class Add(Expr):
    left: Expr
    right: Expr

    def simplify(self) -> Expr:
        global _last_3d
        l = self.left.simplify()
        r = self.right.simplify()

        if isinstance(l, Number) and isinstance(r, Number):
            out = Number(l.value + r.value)
            _last_3d = _build_3d(self, out, "add_fold")
            return out

        if isinstance(l, Number) and l.value == 0:
            _last_3d = _build_3d(self, r, "add_left_zero")
            return r
        if isinstance(r, Number) and r.value == 0:
            _last_3d = _build_3d(self, l, "add_right_zero")
            return l

        out = Add(l, r)
        _last_3d = _build_3d(self, out, "add_simplify")
        return out

    def __str__(self):
        return f"({self.left} + {self.right})"


# ============================================================
# MUL
# ============================================================

@dataclass
class Mul(Expr):
    left: Expr
    right: Expr

    def simplify(self) -> Expr:
        global _last_3d
        l = self.left.simplify()
        r = self.right.simplify()

        if isinstance(l, Number) and isinstance(r, Number):
            out = Number(l.value * r.value)
            _last_3d = _build_3d(self, out, "mul_fold")
            return out

        if (isinstance(l, Number) and l.value == 0) or (isinstance(r, Number) and r.value == 0):
            out = Number(0)
            _last_3d = _build_3d(self, out, "mul_zero")
            return out

        if isinstance(l, Number) and l.value == 1:
            _last_3d = _build_3d(self, r, "mul_left_one")
            return r
        if isinstance(r, Number) and r.value == 1:
            _last_3d = _build_3d(self, l, "mul_right_one")
            return l

        out = Mul(l, r)
        _last_3d = _build_3d(self, out, "mul_simplify")
        return out

    def __str__(self):
        return f"({self.left} * {self.right})"


# ============================================================
# POW
# ============================================================

@dataclass
class Pow(Expr):
    base: Expr
    exp: Expr

    def simplify(self) -> Expr:
        global _last_3d
        b = self.base.simplify()
        e = self.exp.simplify()

        if isinstance(b, Number) and isinstance(e, Number):
            out = Number(b.value ** e.value)
            _last_3d = _build_3d(self, out, "pow_fold")
            return out

        if isinstance(e, Number) and e.value == 1:
            _last_3d = _build_3d(self, b, "pow_one")
            return b
        if isinstance(e, Number) and e.value == 0:
            out = Number(1)
            _last_3d = _build_3d(self, out, "pow_zero")
            return out

        out = Pow(b, e)
        _last_3d = _build_3d(self, out, "pow_simplify")
        return out

    def __str__(self):
        return f"({self.base} ^ {self.exp})"


# ============================================================
# NEG
# ============================================================

@dataclass
class Neg(Expr):
    expr: Expr

    def simplify(self) -> Expr:
        global _last_3d
        e = self.expr.simplify()

        if isinstance(e, Number):
            out = Number(-e.value)
            _last_3d = _build_3d(self, out, "neg_fold")
            return out

        out = Neg(e)
        _last_3d = _build_3d(self, out, "neg_simplify")
        return out

    def __str__(self):
        return f"-({self.expr})"


# ============================================================
# EQ
# ============================================================

@dataclass
class Eq(Expr):
    left: Expr
    right: Expr

    def __str__(self):
        return f"{self.left} = {self.right}"


# ============================================================
# HELPERS
# ============================================================

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
    global _last_3d
    before = expr

    if isinstance(expr, Symbol):
        out = mapping.get(expr.name, expr)
        _last_3d = _build_3d(before, out, "sub_symbol")
        return out

    if isinstance(expr, Number):
        _last_3d = _build_3d(before, expr, "sub_number")
        return expr

    if isinstance(expr, Add):
        out = Add(substitute(expr.left, mapping), substitute(expr.right, mapping)).simplify()
        _last_3d = _build_3d(before, out, "sub_add")
        return out

    if isinstance(expr, Mul):
        out = Mul(substitute(expr.left, mapping), substitute(expr.right, mapping)).simplify()
        _last_3d = _build_3d(before, out, "sub_mul")
        return out

    if isinstance(expr, Pow):
        out = Pow(substitute(expr.base, mapping), substitute(expr.exp, mapping)).simplify()
        _last_3d = _build_3d(before, out, "sub_pow")
        return out

    if isinstance(expr, Neg):
        out = Neg(substitute(expr.expr, mapping)).simplify()
        _last_3d = _build_3d(before, out, "sub_neg")
        return out

    if isinstance(expr, Eq):
        out = Eq(substitute(expr.left, mapping), substitute(expr.right, mapping))
        _last_3d = _build_3d(before, out, "sub_eq")
        return out

    _last_3d = _build_3d(before, expr, "sub_unknown")
    return expr

