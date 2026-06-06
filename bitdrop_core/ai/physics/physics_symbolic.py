from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict


# ============================================================
# SYMBOLIC PHYSICS EQUATION SOLVER
# ============================================================

@dataclass
class PhysicsEquationSolution:
    target: str
    expression: str


def solve_physics_equation(equation: str, target: str) -> Optional[PhysicsEquationSolution]:
    eq = equation.replace(" ", "")
    target = target.strip()

    if "=" not in eq:
        return None

    left, right = eq.split("=", 1)

    # A = B * C
    m = re.match(r"^([A-Za-z]\w*)\*([A-Za-z]\w*)$", right)
    if m:
        b, c = m.groups()
        a = left
        if target == a:
            return PhysicsEquationSolution(a, f"{b} * {c}")
        if target == b:
            return PhysicsEquationSolution(b, f"{a} / {c}")
        if target == c:
            return PhysicsEquationSolution(c, f"{a} / {b}")

    # A = B / C
    m = re.match(r"^([A-Za-z]\w*)/([A-Za-z]\w*)$", right)
    if m:
        b, c = m.groups()
        a = left
        if target == a:
            return PhysicsEquationSolution(a, f"{b} / {c}")
        if target == b:
            return PhysicsEquationSolution(b, f"{a} * {c}")
        if target == c:
            return PhysicsEquationSolution(c, f"{b} / {a}")

    return None


# ============================================================
# UNIT CONVERSION
# ============================================================

_UNIT_FACTORS: Dict[str, float] = {
    "m": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "km": 1000.0,
    "ft": 0.3048,
    "inch": 0.0254,

    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,

    "kg": 1.0,
    "g": 0.001,

    "j": 1.0,
    "kj": 1000.0,

    "w": 1.0,
    "kw": 1000.0,

    "m/s": 1.0,
    "km/h": 1000.0 / 3600.0,
    "mph": 1609.344 / 3600.0,
}


@dataclass
class UnitConversionResult:
    value: float
    unit: str


def convert_unit(value: float, from_unit: str, to_unit: str) -> Optional[UnitConversionResult]:
    fu = from_unit.strip().lower()
    tu = to_unit.strip().lower()

    if fu not in _UNIT_FACTORS or tu not in _UNIT_FACTORS:
        return None

    base = value * _UNIT_FACTORS[fu]
    target = base / _UNIT_FACTORS[tu]
    return UnitConversionResult(target, to_unit)

