from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import re


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class MathIntent3D:
    """
    3D structural view of math-intent detection.

    axis_x: raw text
    axis_y: token/line decomposition
    axis_z: math-likeness score, extracted equation, flags
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# ORIGINAL CONSTANTS
# ------------------------------------------------------------
MATH_CHARS = set("0123456789+-*/^=().xxyz ")


# ------------------------------------------------------------
# INTERNAL: 3D builder
# ------------------------------------------------------------
def _build_3d(text: str, looks_math: bool, equation: str, score: float) -> MathIntent3D:
    lines = (text or "").splitlines()
    tokens = re.findall(r"\S+", text or "")

    axis_z = {
        "looks_like_math": looks_math,
        "equation": equation,
        "math_score": score,
        "tokens": tokens,
        "char_count": len(text or ""),
    }

    return MathIntent3D(
        raw_text=text or "",
        axis_x=text or "",
        axis_y=lines,
        axis_z=axis_z,
    )


# ------------------------------------------------------------
# 3D-AWARE: looks_like_math
# ------------------------------------------------------------
def looks_like_math(text: str) -> bool:
    stripped = text.replace(" ", "")
    if not stripped:
        return False

    math_count = sum(1 for c in stripped if c in MATH_CHARS)
    score = math_count / len(stripped)

    return score > 0.6


# ------------------------------------------------------------
# 3D-AWARE: extract_equation
# ------------------------------------------------------------
def extract_equation(text: str) -> str:
    if "=" in text:
        idx = text.index("=")
        return text[max(0, idx - 20): idx + 20].strip()
    return text.strip()


# ------------------------------------------------------------
# PUBLIC: 3D wrapper
# ------------------------------------------------------------
def analyze_math_intent(text: str) -> Dict[str, Any]:
    """
    Returns:
      {
        "looks_like_math": bool,
        "equation": str,
        "score": float,
        "structure_3d": MathIntent3D
      }
    """

    stripped = text.replace(" ", "")
    if not stripped:
        result = {
            "looks_like_math": False,
            "equation": "",
            "score": 0.0,
        }
        result["structure_3d"] = _build_3d(text, False, "", 0.0)
        return result

    math_count = sum(1 for c in stripped if c in MATH_CHARS)
    score = math_count / len(stripped)

    looks = score > 0.6
    eq = extract_equation(text)

    result = {
        "looks_like_math": looks,
        "equation": eq,
        "score": score,
    }

    result["structure_3d"] = _build_3d(text, looks, eq, score)
    return result
