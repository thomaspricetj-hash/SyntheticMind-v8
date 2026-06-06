from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple, Optional



# ============================================================
# DIMENSIONAL ANALYSIS
# ============================================================

@dataclass(frozen=True)
class Dimension:
    M: int = 0
    L: int = 0
    T: int = 0
    I: int = 0
    Th: int = 0

    def __add__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            M=self.M + other.M,
            L=self.L + other.L,
            T=self.T + other.T,
            I=self.I + other.I,
            Th=self.Th + other.Th,
        )

    def __sub__(self, other: "Dimension") -> "Dimension":
        return Dimension(
            M=self.M - other.M,
            L=self.L - other.L,
            T=self.T - other.T,
            I=self.I - other.I,
            Th=self.Th - other.Th,
        )

    def is_same(self, other: "Dimension") -> bool:
        return (
            self.M == other.M and
            self.L == other.L and
            self.T == other.T and
            self.I == other.I and
            self.Th == other.Th
        )


DIM_NONE = Dimension()
DIM_MASS = Dimension(M=1)
DIM_LENGTH = Dimension(L=1)
DIM_TIME = Dimension(T=1)
DIM_VELOCITY = Dimension(L=1, T=-1)
DIM_ACCEL = Dimension(L=1, T=-2)
DIM_FORCE = Dimension(M=1, L=1, T=-2)
DIM_ENERGY = Dimension(M=1, L=2, T=-2)
DIM_POWER = Dimension(M=1, L=2, T=-3)


@dataclass
class Quantity:
    value: float
    dim: Dimension
    unit: str = ""

    def __mul__(self, other: "Quantity") -> "Quantity":
        return Quantity(
            self.value * other.value,
            self.dim + other.dim,
            f"{self.unit}*{other.unit}".strip("*"),
        )

    def __truediv__(self, other: "Quantity") -> "Quantity":
        return Quantity(
            self.value / other.value,
            self.dim - other.dim,
            f"{self.unit}/{other.unit}".strip("/"),
        )


UNIT_TABLE: Dict[str, Dimension] = {
    "kg": DIM_MASS,
    "g": DIM_MASS,
    "m": DIM_LENGTH,
    "s": DIM_TIME,
    "m/s": DIM_VELOCITY,
    "m/s^2": DIM_ACCEL,
    "n": DIM_FORCE,
    "j": DIM_ENERGY,
    "w": DIM_POWER,
}


def _parse_unit(unit: str) -> Dimension:
    unit = unit.strip().lower()
    if not unit:
        return DIM_NONE
    if unit in UNIT_TABLE:
        return UNIT_TABLE[unit]

    dim = Dimension()
    parts = re.split(r"[*·]", unit)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "/" in part:
            num, den = part.split("/", 1)
            dim = dim + _parse_unit(num)
            dim = dim - _parse_unit(den)
        else:
            dim = dim + UNIT_TABLE.get(part, DIM_NONE)
    return dim


# ============================================================
# VECTOR MATH
# ============================================================

@dataclass
class Vector:
    components: Tuple[float, ...]

    def magnitude(self) -> float:
        import math
        return math.sqrt(sum(c * c for c in self.components))


def parse_vector(text: str) -> Optional[Vector]:
    m = re.search(r"\(([-0-9.,\s]+)\)", text)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(",")]
    try:
        return Vector(tuple(float(p) for p in parts))
    except ValueError:
        return None


# ============================================================
# PHYSICS ENGINE
# ============================================================

class PhysicsEngine:
    """
    Fully upgraded physics engine:
      - momentum, work, power
      - circular motion
      - electricity
      - thermodynamics
      - vector math
      - unit parsing + dimensional analysis
      - natural-language parsing
      - unitless parsing
      - graphing
      - projectile motion
      - basic circuit solving
      - symbolic equation + unit conversion hooks
      - dimensional consistency checker (NEW)
    """

    def __init__(self, base_engine=None, user_id: str = "physics"):
        if base_engine is None:
            base_engine = EchoEngine()
        self.ua = UniversalAI(base_engine)
        self.g = 9.81

    # --------------------------------------------------------
    # Quantity extraction
    # --------------------------------------------------------

    def _extract_quantities(self, text: str) -> Dict[str, Quantity]:
        out: Dict[str, Quantity] = {}

        pattern = r"(\w+)\s*=\s*([0-9.]+)\s*([A-Za-z/^\d]*)"
        for name, val, unit in re.findall(pattern, text):
            try:
                v = float(val)
            except ValueError:
                continue
            dim = _parse_unit(unit)
            out[name.lower()] = Quantity(v, dim, unit)

        synonyms = {
            "mass": "m",
            "weight": "m",
            "velocity": "v",
            "speed": "v",
            "acceleration": "a",
            "force": "f",
            "distance": "d",
            "radius": "r",
            "current": "i",
            "voltage": "v",
            "resistance": "r",
            "temperature": "t",
        }

        for word, key in synonyms.items():
            m = re.search(rf"{word}\s*=\s*([0-9.]+)", text, re.I)
            if m:
                out[key] = Quantity(float(m.group(1)), DIM_NONE, "")

        return out

    # --------------------------------------------------------
    # DIMENSIONAL CONSISTENCY CHECKER (MODULE 5)
    # --------------------------------------------------------

    def _dim_of_symbol(self, name: str, vals: Dict[str, Quantity]) -> Dimension:
        q = vals.get(name.lower())
        if q:
            return q.dim

        # known physics symbols
        if name.lower() == "m":
            return DIM_MASS
        if name.lower() == "v":
            return DIM_VELOCITY
        if name.lower() == "a":
            return DIM_ACCEL
        if name.lower() == "f":
            return DIM_FORCE
        if name.lower() == "t":
            return DIM_TIME
        if name.lower() == "d":
            return DIM_LENGTH

        return DIM_NONE

    def _dim_eval(self, expr: str, vals: Dict[str, Quantity]) -> Dimension:
        """
        Evaluates the dimensional structure of an expression like:
            m * a
            F / t
            (m * v) / t
        """
        expr = expr.replace(" ", "")

        # Parentheses
        while "(" in expr:
            inner = re.search(r"\(([^\(\)]+)\)", expr)
            if not inner:
                break
            sub = inner.group(1)
            dim_sub = self._dim_eval(sub, vals)
            expr = expr.replace(f"({sub})", f"#{dim_sub.M},{dim_sub.L},{dim_sub.T},{dim_sub.I},{dim_sub.Th}#")

        # Replace symbols with dimensions
        def repl(m):
            name = m.group(0)
            d = self._dim_of_symbol(name, vals)
            return f"#{d.M},{d.L},{d.T},{d.I},{d.Th}#"

        expr = re.sub(r"[A-Za-z]+", repl, expr)

        # Now evaluate * and /
        tokens = re.split(r"([*/])", expr)

        # Convert #M,L,T,I,Th# → Dimension
        def parse_dim(tok: str) -> Dimension:
            if not tok.startswith("#"):
                return DIM_NONE
            nums = tok.strip("#").split(",")
            return Dimension(*map(int, nums))

        current = parse_dim(tokens[0])

        i = 1
        while i < len(tokens):
            op = tokens[i]
            nxt = parse_dim(tokens[i + 1])
            if op == "*":
                current = current + nxt
            else:
                current = current - nxt
            i += 2

        return current

    def check_dimensions(self, equation: str) -> str:
        """
        Checks if left and right sides of an equation have matching dimensions.
        """
        if "=" not in equation:
            return "Not an equation."

        left, right = equation.split("=", 1)
        vals = self._extract_quantities(equation)

        dim_left = self._dim_eval(left, vals)
        dim_right = self._dim_eval(right, vals)

        if dim_left.is_same(dim_right):
            return "Dimensions are consistent."
        else:
            return (
                "Dimension mismatch:\n"
                f"  Left:  M{dim_left.M} L{dim_left.L} T{dim_left.T}\n"
                f"  Right: M{dim_right.M} L{dim_right.L} T{dim_right.T}"
            )

    # --------------------------------------------------------
    # CORE SOLVER
    # --------------------------------------------------------

    def solve(self, text: str) -> str:
        t = text.lower()
        vals = self._extract_quantities(text)

        # Dimensional check request
        if "check dimensions" in t or "dimension check" in t:
            return self.check_dimensions(text)

        # Force F = m a
        if "force" in t or ("mass" in t and "acceleration" in t):
            m = vals.get("m")
            a = vals.get("a") or vals.get("acceleration")
            if m and a:
                F = m.value * a.value
                return f"Force = {F} N"

        # Kinetic energy K = 1/2 m v^2
        if "kinetic" in t or ("mass" in t and "velocity" in t):
            m = vals.get("m")
            v = vals.get("v")
            if m and v:
                K = 0.5 * m.value * v.value * v.value
                return f"Kinetic energy = {K} J"

        # Momentum p = m v
        if "momentum" in t:
            m = vals.get("m")
            v = vals.get("v")
            if m and v:
                return f"Momentum = {m.value * v.value} kg·m/s"

        # Work W = F d
        if "work" in t:
            F = vals.get("f")
            d = vals.get("d")
            if F and d:
                return f"Work = {F.value * d.value} J"

        # Power P = F v or W/t
        if "power" in t:
            F = vals.get("f")
            v = vals.get("v")
            W = vals.get("w")
            t_q = vals.get("t")
            if F and v:
                return f"Power = {F.value * v.value} W"
            if W and t_q:
                return f"Power = {W.value / t_q.value} W"

        # Circular motion
        if "centripetal" in t or "circular" in t:
            m = vals.get("m")
            v = vals.get("v")
            r = vals.get("r")
            if m and v and r:
                F = m.value * v.value * v.value / r.value
                return f"Centripetal force = {F} N"

        # Electricity
        if "ohm" in t or "voltage" in t or "current" in t or "resistance" in t:
            V = vals.get("v")
            Iq = vals.get("i")
            R = vals.get("r")
            if Iq and R and not V:
                return f"Voltage = {Iq.value * R.value} V"
            if V and R and not Iq:
                return f"Current = {V.value / R.value} A"
            if V and Iq and not R:
                return f"Resistance = {V.value / Iq.value} ohm"

        # Thermodynamics
        if "heat" in t or "temperature" in t:
            m = vals.get("m")
            c = vals.get("c")
            dT = vals.get("dt")
            if m and c and dT:
                return f"Heat energy = {m.value * c.value * dT.value} J"

        # Vector magnitude
        if "vector" in t and "magnitude" in t:
            v = parse_vector(text)
            if v:
                return f"Vector magnitude = {v.magnitude()}"

        # Projectile motion
        if "projectile" in t or ("launch" in t and "angle" in t):
            return self.projectile(text)

        # Circuit solving
        if "circuit" in t or "series" in t or "parallel" in t:
            res = self.circuit(text)
            if res is not None:
                return res

        # Graphing
        if t.startswith("plot"):
            try:
                import matplotlib.pyplot as plt
                import numpy as np
            except ImportError:
                return "Matplotlib not installed."

            m = re.search(r"plot\s+y\s*=\s*([x0-9+\-*/^. ]+)\s+from\s+([0-9.\-]+)\s+to\s+([0-9.\-]+)", t)
            if not m:
                return "Plot syntax: plot y = <expr> from a to b"

            expr_str, a_str, b_str = m.groups()
            a = float(a_str)
            b = float(b_str)

            xs = np.linspace(a, b, 200)
            ys = []
            for x in xs:
                try:
                    y = eval(expr_str.replace("^", "**"), {"x": x})
                except Exception:
                    y = float("nan")
                ys.append(y)

            plt.plot(xs, ys)
            plt.grid(True)
            plt.show()
            return f"Plotted y = {expr_str}"

        # Fallback
        return self.ua.chat(text, tags={"op": "physics_nlq"})

    # --------------------------------------------------------
    # PROJECTILE MOTION PACK
    # --------------------------------------------------------

    def projectile(self, text: str) -> str:
        t = text.lower()
        vals = self._extract_quantities(text)

        v0 = vals.get("v0") or vals.get("velocity") or vals.get("v")
        angle = vals.get("angle")
        g_q = vals.get("g") or Quantity(self.g, DIM_ACCEL, "m/s^2")

        if not (v0 and angle):
            m_v = re.search(r"(\d+\.?\d*)\s*(m/s)?\s*launch", t)
            m_a = re.search(r"angle\s*=\s*([0-9.]+)", t)
            if m_v and not v0:
                v0 = Quantity(float(m_v.group(1)), DIM_VELOCITY, "m/s")
            if m_a and not angle:
                angle = Quantity(float(m_a.group(1)), DIM_NONE, "deg")

        if not (v0 and angle):
            return "Projectile motion requires velocity and angle."

        import math
        theta = math.radians(angle.value)

        vx = v0.value * math.cos(theta)
        vy = v0.value * math.sin(theta)
        g = g_q.value

        T = 2 * vy / g
        H = (vy ** 2) / (2 * g)
        R = vx * T

        return (
            "Projectile motion results:\n"
            f"  Horizontal velocity vx = {vx:.3f} m/s\n"
            f"  Vertical velocity vy = {vy:.3f} m/s\n"
            f"  Time of flight T = {T:.3f} s\n"
            f"  Maximum height H = {H:.3f} m\n"
            f"  Range R = {R:.3f} m"
        )

    # --------------------------------------------------------
    # CIRCUIT SOLVER PACK
    # --------------------------------------------------------

    def circuit(self, text: str) -> Optional[str]:
        from .circuits import solve_circuit
        res = solve_circuit(text)
        if res is None:
            return None
        return f"Equivalent resistance ({res.kind}) = {res.equivalent_resistance} ohm"

    # --------------------------------------------------------
    # SYMBOLIC PHYSICS + UNIT CONVERSION HOOKS
    # --------------------------------------------------------

    def solve_symbolic(self, equation: str, target: str) -> str:
        from .physics_symbolic import solve_physics_equation
        sol = solve_physics_equation(equation, target)
        if not sol:
            return "Cannot symbolically solve equation"
        return f"{sol.target} = {sol.expression}"

    def convert(self, value: float, from_unit: str, to_unit: str) -> str:
        from .physics_symbolic import convert_unit
        res = convert_unit(value, from_unit, to_unit)
        if not res:
            return "Cannot convert units"
        return f"{res.value} {res.unit}"

