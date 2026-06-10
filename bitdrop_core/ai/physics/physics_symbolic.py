from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, List


# ============================================================
# 3D STRUCTURAL MODELS
# ============================================================

@dataclass
class Equation3D:
    """
    3D structural view of a physics equation.

    axis_x: full raw equation string
    axis_y: [left_side, right_side]
    axis_z:
      - symbols_left:  list of variable symbols on the left
      - symbols_right: list of variable symbols on the right
      - operators:     list of operators on the right side
    """
    raw: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, List[str]]


@dataclass
class Unit3D:
    """
    3D structural view of a unit string.

    axis_x: raw unit string
    axis_y: list of unit tokens (e.g., ["km", "h"])
    axis_z:
      - factors: list of normalized base units (for introspection)
    """
    raw: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, List[str]]


def _build_3d_equation(equation: str) -> Optional[Equation3D]:
    eq = equation.strip()
    if "=" not in eq:
        return None

    left, right = eq.split("=", 1)
    left = left.strip()
    right = right.strip()

    # Extract symbols and operators from the right side
    symbols_right = re.findall(r"[A-Za-z]\w*", right)
    symbols_left = re.findall(r"[A-Za-z]\w*", left)
    operators = re.findall(r"[+\-*/]", right)

    axis_z = {
        "symbols_left": symbols_left,
        "symbols_right": symbols_right,
        "operators": operators,
    }

    return Equation3D(
        raw=eq,
        axis_x=eq,
        axis_y=[left, right],
        axis_z=axis_z,
    )


def _build_3d_unit(unit: str) -> Unit3D:
    raw = unit.strip()
    if not raw:
        return Unit3D(raw="", axis_x="", axis_y=[], axis_z={"factors": []})

    # Split by * and / to get structural tokens
    tokens = re.split(r"[*/]", raw)
    tokens = [t.strip() for t in tokens if t.strip()]

    # For now, factors are just the tokens themselves (no deep dimensional expansion here)
    factors = tokens[:]

    return Unit3D(
        raw=raw,
        axis_x=raw,
        axis_y=tokens,
        axis_z={"factors": factors},
    )


# ============================================================
# SYMBOLIC PHYSICS EQUATION SOLVER (3D-AWARE, LOSSLESS)
# ============================================================

@dataclass
class PhysicsEquationSolution:
    target: str
    expression: str


def solve_physics_equation(equation: str, target: str) -> Optional[PhysicsEquationSolution]:
    """
    3D-aware symbolic solver for very simple algebraic physics equations.

    Supports patterns:
      - A = B * C
      - A = B / C

    Uses a 3D structural view (Equation3D) but remains fully deterministic
    and lossless with respect to the original equation string.
    """
    target = target.strip()
    eq3d = _build_3d_equation(equation)
    if eq3d is None:
        return None

    left, right = eq3d.axis_y
    right_no_space = right.replace(" ", "")

    # A = B * C
    m = re.match(r"^([A-Za-z]\w*)\*([A-Za-z]\w*)$", right_no_space)
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
    m = re.match(r"^([A-Za-z]\w*)/([A-Za-z]\w*)$", right_no_space)
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
# UNIT CONVERSION (3D STRUCTURAL VIEW, SAME BEHAVIOR)
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
    """
    3D-aware unit conversion.

    The 3D view (Unit3D) is built for both source and target units,
    but the numerical conversion behavior remains identical to the
    original implementation: a simple factor lookup in _UNIT_FACTORS.
    """
    fu = from_unit.strip().lower()
    tu = to_unit.strip().lower()

    # Build 3D structural views (for future introspection / debugging)
    _ = _build_3d_unit(fu)
    _ = _build_3d_unit(tu)

    if fu not in _UNIT_FACTORS or tu not in _UNIT_FACTORS:
        return None

    base = value * _UNIT_FACTORS[fu]
    target_val = base / _UNIT_FACTORS[tu]
    return UnitConversionResult(target_val, to_unit)


