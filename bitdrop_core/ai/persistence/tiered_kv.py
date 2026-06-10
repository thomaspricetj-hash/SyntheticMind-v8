from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Tuple, Optional, Dict
import time
import math


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class TieredKV3D:
    """
    3D structural view of a TieredKV operation.

    axis_x: high‑level operation ("get", "set", "delete", "resize", "scan", "stats")
    axis_y: structural decomposition (key, size, capacity)
    axis_z: metadata (latency, probe_steps, prefix, result_len)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# TIERED KV — MAX SPEED + 3D‑MAX
# ============================================================

class TieredKV:
    """
    TieredKV — MAX SPEED EDITION (3D‑MAX)
    ------------------------------------
    Ultra-fast in-memory key/value store using an open-addressing
    hash table with power-of-two capacity.

    Features:
        • O(1) average get/set/delete
        • Preallocated buckets (no dict resize thrash)
        • Bitmask indexing (fast modulo)
        • Linear probing (cache-friendly)
        • Prefix scan
        • Batch get
        • Stats for debugging
    Now includes:
        • 3D‑MAX introspection for every operation
    """

    def __init__(self, initial_capacity: int = 1024):
        cap = 1 << (initial_capacity - 1).bit_length()
        self._capacity = cap
        self._mask = cap - 1

        self._keys: List[Optional[Any]] = [None] * cap
        self._vals: List[Optional[Any]] = [None] * cap
        self._size = 0

        self._last_3d: Optional[TieredKV3D] = None

    # -------------------------------------------------------------
    # Internal: find slot
    # -------------------------------------------------------------
    def _find_slot(self, key) -> Tuple[int, int]:
        """Returns (index, probe_steps)."""
        idx = hash(key) & self._mask
        steps = 0
        while True:
            k = self._keys[idx]
            if k is None or k == key:
                return idx, steps
            idx = (idx + 1) & self._mask
            steps += 1

    # -------------------------------------------------------------
    # Resize
    # -------------------------------------------------------------
    def _resize(self):
        start = time.time()

        old_keys = self._keys
        old_vals = self._vals

        new_cap = self._capacity * 2
        self._capacity = new_cap
        self._mask = new_cap - 1

        self._keys = [None] * new_cap
        self._vals = [None] * new_cap
        self._size = 0

        for k, v in zip(old_keys, old_vals):
            if k is not None:
                self.set(k, v)

        self._last_3d = TieredKV3D(
            axis_x="resize",
            axis_y=[f"new_capacity:{new_cap}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    # -------------------------------------------------------------
    # BASIC OPERATIONS
    # -------------------------------------------------------------
    def get(self, key, default=None):
        start = time.time()

        idx, steps = self._find_slot(key)
        if self._keys[idx] is None:
            out = default
        else:
            out = self._vals[idx]

        self._last_3d = TieredKV3D(
            axis_x="get",
            axis_y=[f"key:{key}", f"found:{out is not default}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "probe_steps": steps,
            },
        )

        return out

    def set(self, key, value):
        start = time.time()

        if self._size * 2 >= self._capacity:
            self._resize()

        idx, steps = self._find_slot(key)
        is_new = self._keys[idx] is None

        if is_new:
            self._size += 1

        self._keys[idx] = key
        self._vals[idx] = value

        self._last_3d = TieredKV3D(
            axis_x="set",
            axis_y=[f"key:{key}", f"new:{is_new}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "probe_steps": steps,
                "size": self._size,
                "capacity": self._capacity,
            },
        )

    put = set

    def delete(self, key):
        start = time.time()

        idx, steps = self._find_slot(key)
        existed = self._keys[idx] is not None

        if not existed:
            self._last_3d = TieredKV3D(
                axis_x="delete",
                axis_y=[f"key:{key}", "missing"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return

        self._keys[idx] = None
        self._vals[idx] = None
        self._size -= 1

        nxt = (idx + 1) & self._mask
        reinserts = 0

        while self._keys[nxt] is not None:
            k = self._keys[nxt]
            v = self._vals[nxt]
            self._keys[nxt] = None
            self._vals[nxt] = None
            self._size -= 1
            self.set(k, v)
            reinserts += 1
            nxt = (nxt + 1) & self._mask

        self._last_3d = TieredKV3D(
            axis_x="delete",
            axis_y=[f"key:{key}", f"reinserts:{reinserts}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "probe_steps": steps,
            },
        )

    def has(self, key) -> bool:
        idx, _ = self._find_slot(key)
        return self._keys[idx] is not None

    # -------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------
    def keys(self) -> List[Any]:
        return [k for k in self._keys if k is not None]

    def values(self) -> List[Any]:
        return [self._vals[i] for i in range(self._capacity) if self._keys[i] is not None]

    def items(self) -> List[Tuple[Any, Any]]:
        return [(self._keys[i], self._vals[i]) for i in range(self._capacity) if self._keys[i] is not None]

    def clear(self):
        self.__init__(initial_capacity=self._capacity)

    # -------------------------------------------------------------
    # Batch + prefix operations
    # -------------------------------------------------------------
    def get_many(self, keys: List[Any]) -> List[Any]:
        start = time.time()
        out = [self.get(k) for k in keys]

        self._last_3d = TieredKV3D(
            axis_x="get_many",
            axis_y=[f"count:{len(keys)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return out

    def prefix_scan(self, prefix: bytes) -> List[Tuple[Any, Any]]:
        start = time.time()

        out = []
        for k, v in self.items():
            if isinstance(k, (bytes, str)) and k.startswith(prefix):
                out.append((k, v))

        self._last_3d = TieredKV3D(
            axis_x="prefix_scan",
            axis_y=[f"prefix:{prefix}", f"matches:{len(out)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return out

    # -------------------------------------------------------------
    # Debugging
    # -------------------------------------------------------------
    def stats(self) -> dict:
        start = time.time()

        out = {
            "size": self._size,
            "capacity": self._capacity,
            "load_factor": self._size / self._capacity,
        }

        self._last_3d = TieredKV3D(
            axis_x="stats",
            axis_y=[f"size:{self._size}", f"capacity:{self._capacity}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return out

    def __contains__(self, key):
        return self.has(key)

    def __len__(self):
        return self._size

    def __repr__(self):
        return f"TieredKV(size={self._size}, capacity={self._capacity})"


