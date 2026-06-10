from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import math
from .symbolic import Expr


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class MathEmbedding3D:
    """
    3D structural view of a math embedding operation.

    axis_x: raw text or expression string
    axis_y: token/char decomposition
    axis_z: embedding metadata (dim, norm, hash-flow)
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: MathEmbedding3D | None = None


# ============================================================
# INTERNAL 3D BUILDER
# ============================================================

def _build_3d(text: str, vec: List[float], hash_flow: List[int]) -> MathEmbedding3D:
    axis_z = {
        "dim": len(vec),
        "norm": math.sqrt(sum(v * v for v in vec)),
        "hash_flow": hash_flow,
        "min_val": min(vec) if vec else 0.0,
        "max_val": max(vec) if vec else 0.0,
    }
    return MathEmbedding3D(
        raw_text=text,
        axis_x=text,
        axis_y=list(text),
        axis_z=axis_z,
    )


# ============================================================
# Deterministic, engine‑independent embedding
# ============================================================

def _fast_hash_embedding(text: str, dim: int = 64):
    """
    A fast, deterministic embedding function that does NOT depend on MathEngine.
    Produces a stable vector suitable for cosine similarity and memory reuse.
    """

    vec = [0.0] * dim
    h = 0
    hash_flow: List[int] = []

    for i, ch in enumerate(text):
        h = (h * 1315423911) ^ ord(ch)
        hash_flow.append(h & 0xFFFF)
        idx = i % dim
        vec[idx] += float((h & 0xFFFF) / 65535.0)

    # L2 normalize
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]

    # Attach 3D structure
    global _last_3d
    _last_3d = _build_3d(text, vec, hash_flow)

    return vec


# ============================================================
# Public API
# ============================================================

def embed_math_text(text: str):
    """
    Deterministic embedding for raw math text.
    Replaces the old BitDrop UniversalAI skimmer.
    """
    return _fast_hash_embedding(text)


def embed_expr(expr: Expr):
    """
    Embed a symbolic expression by converting it to string first.
    """
    s = str(expr)
    return _fast_hash_embedding(s)


