from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
import re


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


def solve_circuit(text: str) -> ResistorNetworkResult | None:
    """
    Very small circuit helper:
      - Detects 'series' or 'parallel'
      - Extracts R1, R2, R3, ... values
      - Computes equivalent resistance
    """
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

    # If not explicitly series/parallel, try to guess:
    # default to series if 'in series' appears, else None
    return None
