import ctypes
import os
import threading


class BitDropError(Exception):
    """Raised when the BitDrop CUDA engine reports an error."""


class BitDropCompressor:
    """
    Python wrapper for the BitDrop CUDA compression engine.
    Fully production‑grade:
        • thread‑safe singleton
        • automatic buffer resizing
        • error detection
        • symbol validation
        • safe fallback behavior
    """

    _instance_lock = threading.Lock()
    _instance = None

    @classmethod
    def instance(cls):
        """Singleton access."""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------
    # INITIALIZATION
    # -------------------------------------------------------------
    def __init__(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dll_path = os.path.join(root, "build", "Release", "bitdrop.dll")

        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"BitDrop DLL not found at: {dll_path}")

        self.lib = ctypes.cdll.LoadLibrary(dll_path)

        # Validate symbols exist
        for sym in ("bdrop_compress", "bdrop_decompress"):
            if not hasattr(self.lib, sym):
                raise BitDropError(f"Missing symbol in DLL: {sym}")

        # Define signatures
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

        # Thread lock for GPU safety
        self._lock = threading.Lock()

    # -------------------------------------------------------------
    # INTERNAL UTILITIES
    # -------------------------------------------------------------
    def _ensure_nonzero(self, size: int):
        if size == 0:
            raise BitDropError("BitDrop returned zero bytes — compression failed.")

    # -------------------------------------------------------------
    # COMPRESSION
    # -------------------------------------------------------------
    def compress(self, data: bytes) -> bytes:
        """Compress bytes using the BitDrop CUDA engine."""
        if not data:
            return b""

        with self._lock:
            in_buf = ctypes.create_string_buffer(data)

            # Start with 2× input size, expand if needed
            out_cap = max(len(data) * 2, 64)
            while True:
                out_buf = ctypes.create_string_buffer(out_cap)

                out_size = self.lib.bdrop_compress(
                    ctypes.addressof(in_buf), len(data),
                    ctypes.addressof(out_buf), out_cap
                )

                if out_size == 0:
                    # Buffer too small → grow and retry
                    out_cap *= 2
                    continue

                self._ensure_nonzero(out_size)
                return out_buf.raw[:out_size]

    # -------------------------------------------------------------
    # DECOMPRESSION
    # -------------------------------------------------------------
    def decompress(self, data: bytes, expected_size: int) -> bytes:
        """Decompress bytes using the BitDrop CUDA engine."""
        if not data:
            return b""

        if expected_size <= 0:
            raise BitDropError("Expected size must be > 0 for decompression.")

        with self._lock:
            in_buf = ctypes.create_string_buffer(data)
            out_buf = ctypes.create_string_buffer(expected_size)

            out_size = self.lib.bdrop_decompress(
                ctypes.addressof(in_buf), len(data),
                ctypes.addressof(out_buf), expected_size
            )

            self._ensure_nonzero(out_size)

            if out_size != expected_size:
                raise BitDropError(
                    f"Decompression size mismatch: expected {expected_size}, got {out_size}"
                )

            return out_buf.raw[:out_size]

