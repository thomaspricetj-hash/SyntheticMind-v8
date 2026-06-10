# syntheticmind/tools/file_tool.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import os
import time
import traceback


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class File3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# FILE TOOL — MAX I/O + 3D‑MAX
# ============================================================

class FileTool:
    """
    Robust file operations with structured envelopes (3D‑MAX Edition).

    Supports:
        • safe read/write
        • auto-create directories
        • UTF-8 text mode
        • structured error reporting
        • latency measurement
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self._last_3d: Optional[File3D] = None

    # ------------------------------------------------------------
    # READ FILE
    # ------------------------------------------------------------
    def read(self, path: str) -> Dict[str, Any]:
        start = time.time()

        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"file not found: {path}")

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

            latency = int((time.time() - start) * 1000)

            self._last_3d = File3D(
                axis_x="read",
                axis_y=[f"path:{path}"],
                axis_z={
                    "latency_ms": latency,
                    "bytes": len(content.encode("utf-8")),
                    "ok": True,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "path": path,
                "content": content,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = File3D(
                axis_x="read",
                axis_y=[f"path:{path}", "exception"],
                axis_z={
                    "latency_ms": latency,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "path": path,
                "content": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # WRITE FILE
    # ------------------------------------------------------------
    def write(self, path: str, content: str) -> Dict[str, Any]:
        start = time.time()

        try:
            directory = os.path.dirname(path)
            created_dir = False

            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                created_dir = True

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            bytes_written = len(content.encode("utf-8"))
            latency = int((time.time() - start) * 1000)

            self._last_3d = File3D(
                axis_x="write",
                axis_y=[f"path:{path}"],
                axis_z={
                    "latency_ms": latency,
                    "bytes_written": bytes_written,
                    "created_dir": created_dir,
                    "ok": True,
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
                "path": path,
                "bytes_written": bytes_written,
                "error": None,
            }

        except Exception as e:
            latency = int((time.time() - start) * 1000)

            self._last_3d = File3D(
                axis_x="write",
                axis_y=[f"path:{path}", "exception"],
                axis_z={
                    "latency_ms": latency,
                    "error": str(e),
                },
            )

            return {
                "ok": False,
                "latency_ms": latency,
                "path": path,
                "bytes_written": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

