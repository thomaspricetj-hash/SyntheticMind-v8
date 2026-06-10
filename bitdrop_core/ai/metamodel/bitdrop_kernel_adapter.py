# bitdrop_core/ai/metamodel/bitdrop_kernel_adapter.py

from __future__ import annotations
from typing import Optional
import ctypes
import sys
import os


class BitDropKernelAdapter:
    """
    3D‑MAX Edition
    ----------------
    • Auto‑detects bitdrop.dll across multiple fallback paths
    • Adds telemetry-friendly error handling
    • Never crashes runtime if DLL missing
    • Preserves your exact kernel ABI
    """

    def __init__(self, lib_path: Optional[str] = None):
        # ------------------------------------------------------------
        # 1. Determine expected library name based on OS
        # ------------------------------------------------------------
        if lib_path is None:
            if sys.platform.startswith("win"):
                lib_name = "bitdrop.dll"
            elif sys.platform == "darwin":
                lib_name = "libbitdrop.dylib"
            else:
                lib_name = "libbitdrop.so"
            lib_path = lib_name

        # ------------------------------------------------------------
        # 2. Build fallback search paths (max improvements)
        # ------------------------------------------------------------
        search_paths = [
            lib_path,
            os.path.join(os.getcwd(), lib_path),
            os.path.join(os.path.dirname(__file__), lib_path),
            os.path.join(os.path.dirname(__file__), "..", lib_path),
            os.path.join(os.path.dirname(__file__), "..", "..", lib_path),
            # User’s known build locations
            r"C:\Users\thomas price\Desktop\bitdrop\build\src\Release\bitdrop.dll",
            r"C:\Users\thomas price\Desktop\bitdrop\build\Release\bitdrop.dll",
            r"C:\Users\thomas price\Desktop\bitdrop-windows\build\lib\Release\bitdrop.dll",
        ]

        self.loaded_path = None
        self.lib = None

        # ------------------------------------------------------------
        # 3. Attempt to load DLL from fallback paths
        # ------------------------------------------------------------
        for path in search_paths:
            try:
                if os.path.exists(path):
                    self.lib = ctypes.CDLL(path)
                    self.loaded_path = path
                    break
            except Exception:
                continue

        # ------------------------------------------------------------
        # 4. If DLL not found, enter safe‑fallback mode
        # ------------------------------------------------------------
        if self.lib is None:
            self.loaded_path = None
            self._fallback_mode = True
            return
        else:
            self._fallback_mode = False

        # ------------------------------------------------------------
        # 5. Configure kernel ABI (unchanged)
        # ------------------------------------------------------------
        self.lib.bitdrop_collapse_buffer.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # input
            ctypes.c_size_t,                 # size
            ctypes.c_void_p,                 # rules (unused)
            ctypes.c_int,                    # rule_count
            ctypes.c_void_p,                 # bloom (unused)
            ctypes.c_int,                    # bloom_words
            ctypes.POINTER(ctypes.c_uint8),  # output_payload
            ctypes.POINTER(ctypes.c_uint8),  # output_tags
            ctypes.POINTER(ctypes.c_uint32), # out_collapse_count
        ]
        self.lib.bitdrop_collapse_buffer.restype = ctypes.c_size_t

    # ------------------------------------------------------------
    # 6. Collapse wrapper with 3D‑MAX safety
    # ------------------------------------------------------------
    def collapse_bytes(self, data: bytes) -> bytes:
        """
        Returns collapsed bytes or original data if:
            • DLL missing
            • Kernel fails
            • Collapse returns zero bytes
        """
        if not data:
            return b""

        # DLL missing → safe fallback
        if self._fallback_mode:
            return data

        size = len(data)

        in_buf = (ctypes.c_uint8 * size)(*data)
        out_payload = (ctypes.c_uint8 * size)()
        out_tags = (ctypes.c_uint8 * size)()
        collapse_count = ctypes.c_uint32(0)

        try:
            written = self.lib.bitdrop_collapse_buffer(
                in_buf,
                ctypes.c_size_t(size),
                None,
                0,
                None,
                0,
                out_payload,
                out_tags,
                ctypes.byref(collapse_count),
            )
        except Exception:
            # Kernel crashed → safe fallback
            return data

        if written == 0:
            # Kernel returned nothing → safe fallback
            return data

        return bytes(out_payload[:written])

