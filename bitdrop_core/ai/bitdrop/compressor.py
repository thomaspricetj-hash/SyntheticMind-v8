from __future__ import annotations
import ctypes
import os
import threading
from dataclasses import dataclass
from typing import Optional, Dict, Any


class BitDropError(Exception):
    """Raised when the BitDrop CUDA engine reports an error or misconfiguration."""


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class BitDrop3D:
    """
    3D structural view of a BitDrop compression/decompression operation.

    axis_x: high-level operation ("compress", "decompress", "init")
    axis_y: structural decomposition (dll_path, op, size info)
    axis_z: metadata (sizes, retries, errors, thread info)
    """
    axis_x: str
    axis_y: list[str]
    axis_z: Dict[str, Any]


# ============================================================
# BITDROP COMPRESSOR (3D‑MAX)
# ============================================================

class BitDropCompressor:
    """
    Python wrapper for the BitDrop CUDA compression engine.

    Features:
        • Thread‑safe singleton
        • Automatic buffer resizing on compression
        • Strict error detection and validation
        • Configurable DLL path via environment
        • Clear, actionable error messages
        • 3D‑MAX introspection of all operations

    Runtime contract:
        • compress(data: bytes) -> bytes
          - returns: [8‑byte little‑endian original_size][compressed_payload]
        • decompress(data: bytes) -> bytes
          - reads original_size from header and uses it for CUDA decompression
    """

    _instance_lock = threading.Lock()
    _instance: Optional["BitDropCompressor"] = None

    @classmethod
    def instance(cls) -> "BitDropCompressor":
        """Return the global singleton instance."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------
    def __init__(self):
        self._last_3d: Optional[BitDrop3D] = None

        env_path = os.environ.get("BITDROP_DLL_PATH")

        if env_path:
            dll_path = os.path.abspath(env_path)
        else:
            root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            dll_path = os.path.join(root, "build", "Release", "bitdrop.dll")

        if not os.path.exists(dll_path):
            self._last_3d = BitDrop3D(
                axis_x="init",
                axis_y=["dll_missing", dll_path],
                axis_z={"error": "dll_not_found"},
            )
            raise FileNotFoundError(
                f"BitDrop DLL not found at: {dll_path}. "
                f"Set BITDROP_DLL_PATH to override the location."
            )

        try:
            self.lib = ctypes.cdll.LoadLibrary(dll_path)
        except OSError as e:
            self._last_3d = BitDrop3D(
                axis_x="init",
                axis_y=["dll_load_failed", dll_path],
                axis_z={"error": str(e)},
            )
            raise BitDropError(f"Failed to load BitDrop DLL at {dll_path}: {e}") from e

        for sym in ("bdrop_compress", "bdrop_decompress"):
            if not hasattr(self.lib, sym):
                self._last_3d = BitDrop3D(
                    axis_x="init",
                    axis_y=["missing_symbol", sym],
                    axis_z={"dll_path": dll_path},
                )
                raise BitDropError(f"Missing symbol in DLL: {sym}")

        self.lib.bdrop_compress.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
            ctypes.c_void_p, ctypes.c_size_t,
        ]
        self.lib.bdrop_compress.restype = ctypes.c_size_t

        self.lib.bdrop_decompress.argtypes = [
            ctypes.c_void_p, ctypes.c_size_t,
            ctypes.c_void_p, ctypes.c_size_t,
        ]
        self.lib.bdrop_decompress.restype = ctypes.c_size_t

        self._lock = threading.Lock()

        self._last_3d = BitDrop3D(
            axis_x="init",
            axis_y=["ok", dll_path],
            axis_z={"status": "initialized"},
        )

    # -------------------------------------------------------------
    # INTERNAL UTILITIES
    # -------------------------------------------------------------
    @staticmethod
    def _ensure_nonzero(size: int, context: str) -> None:
        if size == 0:
            raise BitDropError(f"BitDrop returned zero bytes — {context} failed.")

    # -------------------------------------------------------------
    # COMPRESSION
    # -------------------------------------------------------------
    def compress(self, data: bytes) -> bytes:
        """
        Compress bytes using the BitDrop CUDA engine.

        Layout:
            [8‑byte little‑endian original_size][compressed_payload]

        Returns:
            Compressed bytes. Empty input returns empty bytes.
        """
        if not data:
            self._last_3d = BitDrop3D(
                axis_x="compress",
                axis_y=["empty_input"],
                axis_z={"input_size": 0, "output_size": 0},
            )
            return b""

        original_size = len(data)

        with self._lock:
            in_buf = ctypes.create_string_buffer(data)

            out_cap = max(original_size * 2, 64)
            retries = 0

            while True:
                out_buf = ctypes.create_string_buffer(out_cap)

                out_size = self.lib.bdrop_compress(
                    ctypes.addressof(in_buf), original_size,
                    ctypes.addressof(out_buf), out_cap
                )

                if out_size == 0:
                    out_cap *= 2
                    retries += 1
                    continue

                self._ensure_nonzero(out_size, "compression")

                compressed_payload = out_buf.raw[:out_size]
                header = original_size.to_bytes(8, byteorder="little", signed=False)
                result = header + compressed_payload

                self._last_3d = BitDrop3D(
                    axis_x="compress",
                    axis_y=["compress", f"retries:{retries}"],
                    axis_z={
                        "input_size": original_size,
                        "output_size": len(result),
                        "payload_size": out_size,
                        "retries": retries,
                    },
                )

                return result

    # -------------------------------------------------------------
    # DECOMPRESSION
    # -------------------------------------------------------------
    def decompress(self, data: bytes) -> bytes:
        """
        Decompress bytes using the BitDrop CUDA engine.

        Expects:
            [8‑byte little‑endian original_size][compressed_payload]

        Returns:
            Decompressed bytes of length original_size.

        Raises:
            BitDropError if sizes mismatch or engine reports failure.
        """
        if not data:
            self._last_3d = BitDrop3D(
                axis_x="decompress",
                axis_y=["empty_input"],
                axis_z={"input_size": 0},
            )
            return b""

        if len(data) < 8:
            self._last_3d = BitDrop3D(
                axis_x="decompress",
                axis_y=["missing_header"],
                axis_z={"input_size": len(data)},
            )
            raise BitDropError("Compressed data too small to contain size header.")

        original_size = int.from_bytes(data[:8], byteorder="little", signed=False)
        if original_size <= 0:
            self._last_3d = BitDrop3D(
                axis_x="decompress",
                axis_y=["invalid_original_size"],
                axis_z={"original_size": original_size},
            )
            raise BitDropError("Original size in header must be > 0 for decompression.")

        payload = data[8:]

        with self._lock:
            in_buf = ctypes.create_string_buffer(payload)
            out_buf = ctypes.create_string_buffer(original_size)

            out_size = self.lib.bdrop_decompress(
                ctypes.addressof(in_buf), len(payload),
                ctypes.addressof(out_buf), original_size
            )

            self._ensure_nonzero(out_size, "decompression")

            if out_size != original_size:
                self._last_3d = BitDrop3D(
                    axis_x="decompress",
                    axis_y=["size_mismatch"],
                    axis_z={
                        "input_size": len(payload),
                        "expected_size": original_size,
                        "actual_size": out_size,
                    },
                )
                raise BitDropError(
                    f"Decompression size mismatch: expected {original_size}, got {out_size}"
                )

            result = out_buf.raw[:out_size]

            self._last_3d = BitDrop3D(
                axis_x="decompress",
                axis_y=["decompress", "ok"],
                axis_z={
                    "input_size": len(payload),
                    "output_size": out_size,
                },
            )

            return result




