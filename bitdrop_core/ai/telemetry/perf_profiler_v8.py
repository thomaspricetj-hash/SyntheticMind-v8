# bitdrop_core/ai/telemetry/perf_profiler_v8.py

from __future__ import annotations

import time
import contextlib
import threading
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger("syntheticmind.perf_profiler_v8")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Perf3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# PERF PROFILER V8 — MAX SPEED + 3D‑MAX
# ============================================================

class PerfProfilerV8:
    """
    SyntheticMind v8 Perf Profiler (3D‑MAX Edition)

    Goals:
      - Minimal overhead
      - Fiber/async friendly
      - No external deps
      - Easy integration into router, helpers, memory, tools
      - Structured metrics for telemetry / dashboards
      - 3D‑MAX introspection for every section
    """

    def __init__(self, metrics_hook: Optional[Callable[[str, Dict[str, Any]], None]] = None) -> None:
        self._lock = threading.Lock()
        self._sections: Dict[str, Dict[str, Any]] = {}
        self._metrics_hook = metrics_hook
        self._last_3d: Optional[Perf3D] = None

    # ------------------------------------------------------------
    # SYNC SECTION
    # ------------------------------------------------------------
    @contextlib.contextmanager
    def section(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            duration = end - start
            self._record(name, duration)

    # ------------------------------------------------------------
    # ASYNC SECTION
    # ------------------------------------------------------------
    @contextlib.asynccontextmanager
    async def asection(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            duration = end - start
            self._record(name, duration)

    # ------------------------------------------------------------
    # INTERNAL RECORD
    # ------------------------------------------------------------
    def _record(self, name: str, duration: float) -> None:
        with self._lock:
            s = self._sections.setdefault(name, {
                "count": 0,
                "total": 0.0,
                "min": None,
                "max": None,
            })
            s["count"] += 1
            s["total"] += duration
            s["min"] = duration if s["min"] is None else min(s["min"], duration)
            s["max"] = duration if s["max"] is None else max(s["max"], duration)

        # 3D‑MAX telemetry
        self._last_3d = Perf3D(
            axis_x="_record",
            axis_y=[f"section:{name}"],
            axis_z={
                "duration": duration,
                "count": s["count"],
                "min": s["min"],
                "max": s["max"],
            },
        )

        # Optional external metrics hook
        if self._metrics_hook:
            try:
                self._metrics_hook("perf_section", {
                    "name": name,
                    "duration": duration,
                })
            except Exception:
                pass

    # ------------------------------------------------------------
    # SNAPSHOT
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            out: Dict[str, Dict[str, float]] = {}
            for name, s in self._sections.items():
                count = max(1, s["count"])
                out[name] = {
                    "count": float(s["count"]),
                    "total": float(s["total"]),
                    "avg": float(s["total"]) / count,
                    "min": float(s["min"] or 0.0),
                    "max": float(s["max"] or 0.0),
                }

        self._last_3d = Perf3D(
            axis_x="snapshot",
            axis_y=[f"sections:{len(out)}"],
            axis_z={"ok": True},
        )

        return out

    # ------------------------------------------------------------
    # LOG SNAPSHOT
    # ------------------------------------------------------------
    def log_snapshot(self, prefix: str = "PERF") -> None:
        snap = self.snapshot()

        for name, stats in sorted(snap.items(), key=lambda kv: kv[1]["total"], reverse=True):
            logger.info(
                "%s %s: count=%d total=%.6f avg=%.6f min=%.6f max=%.6f",
                prefix,
                name,
                int(stats["count"]),
                stats["total"],
                stats["avg"],
                stats["min"],
                stats["max"],
            )

        self._last_3d = Perf3D(
            axis_x="log_snapshot",
            axis_y=[f"sections:{len(snap)}"],
            axis_z={"logged": True},
        )


