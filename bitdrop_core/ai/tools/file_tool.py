# syntheticmind/tools/file_tool.py

from __future__ import annotations
from typing import Dict, Any
import os
import time
import traceback


class FileTool:
    """
    Robust file operations with structured envelopes.

    Supports:
        • safe read/write
        • auto-create directories
        • UTF-8 text mode
        • structured error reporting
        • latency measurement
    """

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

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "path": path,
                "content": content,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
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
            # Ensure directory exists
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "path": path,
                "bytes_written": len(content.encode("utf-8")),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "path": path,
                "bytes_written": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

