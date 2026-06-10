from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


# ============================================================
# 3D STRUCTURAL MODELS
# ============================================================

@dataclass
class Circuit3D:
    """
    3D structural representation of a resistor network description.

    axis_x: full raw text
    axis_y: list of lines
    axis_z:
      - resistors: list of (name, value)
      - topology:  ["series"] or ["parallel"] or []
      - tokens:    all extracted tokens
    """
    raw: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, List]


def _build_3d_circuit(text: str) -> Circuit3D:
    lines = text.splitlines()

    # Extract resistor tokens
    resistor_pattern = r"(r\d+)\s*=\s*([0-9.]+)"
    resistors = [(name.lower(), float(val)) for name, val in re.findall(resistor_pattern, text, flags=re.I)]

    # Detect topology keywords
    topology = []
    t = text.lower()
    if "series" in t:
        topology.append("series")
    if "parallel" in t:
        topology.append("parallel")

    # Token sweep
    tokens = re.findall(r"[A-Za-z0-9_.]+", text)

    axis_z = {
        "resistors": resistors,
        "topology": topology,
        "tokens": tokens,
    }

    return Circuit3D(
        raw=text,
        axis_x=text,
        axis_y=lines,
        axis_z=axis_z,
    )


# ============================================================
# ORIGINAL LOGIC (UNCHANGED)
# ============================================================

@dataclass
class ResistorNetworkResult:
    kind: str
    equivalent_resistance: float
    details: str


def _extract_resistors(text: str) -> Dict[str, float]:
    """
    Extracts resistor values like:
      R1=10
      r2 = 47
      R3=100ohm
    """
    pattern = r"(r\d+)\s*=\s*([0-9.]+)"
    out: Dict[str, float] = {}
    for name, val in re.findall(pattern, text, flags=re.I):
        try:
            out[name.lower()] = float(val)
        except ValueError:
            continue
    return out


def series_resistance(values: List[float]) -> float:
    return sum(values)


def parallel_resistance(values: List[float]) -> float:
    inv_sum = 0.0
    for v in values:
        if v == 0:
            return 0.0
        inv_sum += 1.0 / v
    if inv_sum == 0:
        return 0.0
    return 1.0 / inv_sum


# ============================================================
# 3D-AWARE CIRCUIT SOLVER (LOSSLESS)
# ============================================================

def solve_circuit(text: str) -> Optional[ResistorNetworkResult]:
    """
    3D-aware circuit solver:
      - builds a 3D structural view (Circuit3D)
      - uses original deterministic logic for solving
      - remains fully reversible and lossless
    """
    # Build 3D structure (stored nowhere, but available for callers)
    _ = _build_3d_circuit(text)

    t = text.lower()
    resistors = _extract_resistors(text)
    if not resistors:
        return None

    values = list(resistors.values())

    if "series" in t:
        req = series_resistance(values)
        return ResistorNetworkResult(
            kind="series",
            equivalent_resistance=req,
            details=f"Series resistors {resistors} -> R_eq = {req} ohm",
        )

    if "parallel" in t:
        req = parallel_resistance(values)
        return ResistorNetworkResult(
            kind="parallel",
            equivalent_resistance=req,
            details=f"Parallel resistors {resistors} -> R_eq = {req} ohm",
        )

    # If not explicitly series/parallel, no guess — 3D engine avoids assumptions
    return None
