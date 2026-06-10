from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

import numpy as np


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class VectorIndex3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# VECTOR INDEX — MAX SPEED + 3D‑MAX
# ============================================================

class VectorIndex:
    """
    Ultra‑fast in‑memory vector index (3D‑MAX / MAX‑SPEED EDITION)

    Key optimizations:
        - Preallocated matrix with geometric growth (2x expansion)
        - No repeated vstack (removes O(N²) behavior)
        - SIMD‑friendly normalization
        - Vectorized cosine search
        - Optional dimension locking
        - Zero Python loops in hot path
        - 3D‑MAX telemetry for add/search operations
    """

    def __init__(self, path: str, initial_capacity: int = 1024):
        self.path = path  # reserved for future persistence

        self._ids: List[bytes] = []
        self._matrix: Optional[np.ndarray] = None
        self._capacity = initial_capacity
        self._dim = None  # locked after first vector

        self._last_3d: Optional[VectorIndex3D] = None

    # ---------------------------------------------------------
    # Internal: ensure capacity
    # ---------------------------------------------------------
    def _ensure_capacity(self):
        if self._matrix is None:
            return

        if len(self._ids) < self._capacity:
            return

        new_cap = self._capacity * 2
        new_matrix = np.zeros((new_cap, self._dim), dtype=np.float32)
        new_matrix[: self._capacity] = self._matrix

        self._matrix = new_matrix
        self._capacity = new_cap

    # ---------------------------------------------------------
    # Add vector
    # ---------------------------------------------------------
    def add(self, doc_id: bytes, vector: np.ndarray) -> None:
        start = time.time()

        vec = vector.astype(np.float32, copy=False)

        # Lock dimension on first insert
        if self._dim is None:
            self._dim = vec.shape[0]
            self._matrix = np.zeros((self._capacity, self._dim), dtype=np.float32)

        # Dimension mismatch → ignore for max speed
        if vec.shape[0] != self._dim:
            self._last_3d = VectorIndex3D(
                axis_x="add",
                axis_y=[f"doc_id_len:{len(doc_id)}"],
                axis_z={"ok": False, "reason": "dim_mismatch"},
            )
            return

        # Normalize (SIMD‑friendly)
        norm = np.linalg.norm(vec)
        if norm == 0:
            self._last_3d = VectorIndex3D(
                axis_x="add",
                axis_y=[f"doc_id_len:{len(doc_id)}"],
                axis_z={"ok": False, "reason": "zero_norm"},
            )
            return

        vec = vec / norm

        # Ensure capacity
        self._ensure_capacity()

        # Insert row
        idx = len(self._ids)
        self._matrix[idx] = vec
        self._ids.append(doc_id)

        self._last_3d = VectorIndex3D(
            axis_x="add",
            axis_y=[f"doc_id_len:{len(doc_id)}"],
            axis_z={
                "ok": True,
                "index": idx,
                "count": len(self._ids),
                "capacity": self._capacity,
            },
        )

    # ---------------------------------------------------------
    # Search top‑k
    # ---------------------------------------------------------
    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[bytes, float]]:
        start = time.time()

        if self._matrix is None or len(self._ids) == 0:
            self._last_3d = VectorIndex3D(
                axis_x="search",
                axis_y=["empty"],
                axis_z={"ok": True, "returned": 0},
            )
            return []

        q = query_vector.astype(np.float32, copy=False)
        if q.shape[0] != self._dim:
            self._last_3d = VectorIndex3D(
                axis_x="search",
                axis_y=["dim_mismatch"],
                axis_z={"ok": False, "returned": 0},
            )
            return []

        # Normalize query
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            self._last_3d = VectorIndex3D(
                axis_x="search",
                axis_y=["zero_norm"],
                axis_z={"ok": False, "returned": 0},
            )
            return []

        q = q / q_norm

        count = len(self._ids)
        scores = self._matrix[:count] @ q  # vectorized cosine similarity

        # Top‑k selection
        if top_k >= count:
            idx = np.argsort(scores)[::-1]
        else:
            idx = np.argpartition(scores, -top_k)[-top_k:]
            idx = idx[np.argsort(scores[idx])[::-1]]

        results = [(self._ids[i], float(scores[i])) for i in idx]

        self._last_3d = VectorIndex3D(
            axis_x="search",
            axis_y=[f"top_k:{top_k}"],
            axis_z={
                "ok": True,
                "returned": len(results),
                "latency_ms": int((time.time() - start) * 1000),
            },
        )

        return results


