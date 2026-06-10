from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import time


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class DatasetStore3D:
    """
    3D structural view of a DatasetStore operation.

    axis_x: high‑level operation ("add", "get", "get_last", "prefix_scan", "delete", "stats")
    axis_y: structural decomposition (dataset name, record count, capacity)
    axis_z: metadata (latency, sizes, prefix, result_len)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# DATASET STORE — MAX SPEED + 3D‑MAX
# ============================================================

class DatasetStore:
    """
    DatasetStore — MAX SPEED EDITION (3D‑MAX)
    ----------------------------------------
    Ultra-fast in-memory dataset logger.

    Optimizations:
        • Append-only hot path (O(1))
        • Preallocated list blocks for speed
        • Zero serialization overhead
        • Prefix scan for analytics
        • get_last(n) for fast tail reads
        • stats() for debugging
    Now includes:
        • 3D‑MAX introspection for every operation
    """

    def __init__(self, initial_capacity: int = 1024):
        self._datasets: Dict[str, List[Any]] = {}
        self._sizes: Dict[str, int] = {}
        self._initial_capacity = initial_capacity
        self._last_3d: Optional[DatasetStore3D] = None

    # -------------------------------------------------------------
    # Add record
    # -------------------------------------------------------------
    def add(self, name: str, record: Any) -> None:
        start = time.time()

        if name not in self._datasets:
            self._datasets[name] = [None] * self._initial_capacity
            self._sizes[name] = 0

        size = self._sizes[name]

        if size >= len(self._datasets[name]):
            new_cap = len(self._datasets[name]) * 2
            new_list = [None] * new_cap
            old = self._datasets[name]
            new_list[:size] = old[:size]
            self._datasets[name] = new_list

        self._datasets[name][size] = record
        self._sizes[name] += 1

        self._last_3d = DatasetStore3D(
            axis_x="add",
            axis_y=[
                f"name:{name}",
                f"size:{self._sizes[name]}",
                f"capacity:{len(self._datasets[name])}",
            ],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "record_type": type(record).__name__,
            },
        )

    # -------------------------------------------------------------
    # Retrieve all records
    # -------------------------------------------------------------
    def get(self, name: str) -> Optional[List[Any]]:
        start = time.time()

        if name not in self._datasets:
            self._last_3d = DatasetStore3D(
                axis_x="get",
                axis_y=[f"name:{name}", "missing"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return None

        size = self._sizes[name]
        out = self._datasets[name][:size]

        self._last_3d = DatasetStore3D(
            axis_x="get",
            axis_y=[f"name:{name}", f"size:{size}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "result_len": len(out),
            },
        )

        return out

    # -------------------------------------------------------------
    # Retrieve last N records
    # -------------------------------------------------------------
    def get_last(self, name: str, n: int) -> List[Any]:
        start = time.time()

        if name not in self._datasets:
            self._last_3d = DatasetStore3D(
                axis_x="get_last",
                axis_y=[f"name:{name}", "missing"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return []

        size = self._sizes[name]
        start_idx = max(0, size - n)
        out = self._datasets[name][start_idx:size]

        self._last_3d = DatasetStore3D(
            axis_x="get_last",
            axis_y=[f"name:{name}", f"requested:{n}", f"returned:{len(out)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return out

    # -------------------------------------------------------------
    # Prefix scan (analytics)
    # -------------------------------------------------------------
    def prefix_scan(self, prefix: str) -> Dict[str, List[Any]]:
        start = time.time()

        out = {}
        for name in self._datasets:
            if name.startswith(prefix):
                size = self._sizes[name]
                out[name] = self._datasets[name][:size]

        self._last_3d = DatasetStore3D(
            axis_x="prefix_scan",
            axis_y=[f"prefix:{prefix}", f"matches:{len(out)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return out

    # -------------------------------------------------------------
    # Delete dataset
    # -------------------------------------------------------------
    def delete(self, name: str) -> None:
        start = time.time()

        existed = name in self._datasets
        if existed:
            del self._datasets[name]
            del self._sizes[name]

        self._last_3d = DatasetStore3D(
            axis_x="delete",
            axis_y=[f"name:{name}", f"existed:{existed}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    # -------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------
    def has(self, name: str) -> bool:
        return name in self._datasets

    def list(self) -> List[str]:
        return list(self._datasets.keys())

    def clear(self) -> None:
        self._datasets.clear()
        self._sizes.clear()
        self._last_3d = DatasetStore3D(
            axis_x="clear",
            axis_y=["all"],
            axis_z={"cleared": True},
        )

    # -------------------------------------------------------------
    # Debugging
    # -------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        start = time.time()

        out = {
            name: {
                "records": self._sizes[name],
                "capacity": len(self._datasets[name]),
                "load_factor": self._sizes[name] / len(self._datasets[name]),
            }
            for name in self._datasets
        }

        self._last_3d = DatasetStore3D(
            axis_x="stats",
            axis_y=[f"datasets:{len(self._datasets)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "keys": list(self._datasets.keys()),
            },
        )

        return out

    # -------------------------------------------------------------
    # Python protocol helpers
    # -------------------------------------------------------------
    def __contains__(self, name: str) -> bool:
        return name in self._datasets

    def __len__(self) -> int:
        return sum(self._sizes[name] for name in self._datasets)

    def __repr__(self) -> str:
        return f"DatasetStore(datasets={len(self._datasets)})"
