# bitdrop_core/ai/metamodel/bitdrop_kernel_adapter.py

from __future__ import annotations
from typing import Optional
import ctypes
import sys


class BitDropKernelAdapter:
    """
    Thin adapter over the GPU BitDrop kernel.

    Exposes:
        • collapse_bytes(data) -> bytes
    """

    def __init__(self, lib_path: Optional[str] = None):
        if lib_path is None:
            if sys.platform.startswith("win"):
                lib_name = "bitdrop.dll"
            elif sys.platform == "darwin":
                lib_name = "libbitdrop.dylib"
            else:
                lib_name = "libbitdrop.so"
            lib_path = lib_name

        self.lib = ctypes.CDLL(lib_path)

        # uint8_t*, size_t, CollapseRule*, int, uint32_t*, int, uint8_t*, uint8_t*, uint32_t*
        self.lib.bitdrop_collapse_buffer.argtypes = [
            ctypes.POINTER(ctypes.c_uint8),  # input
            ctypes.c_size_t,                 # size
            ctypes.c_void_p,                 # rules (for now, null)
            ctypes.c_int,                    # rule_count
            ctypes.c_void_p,                 # bloom (for now, null)
            ctypes.c_int,                    # bloom_words
            ctypes.POINTER(ctypes.c_uint8),  # output_payload
            ctypes.POINTER(ctypes.c_uint8),  # output_tags
            ctypes.POINTER(ctypes.c_uint32), # out_collapse_count
        ]
        self.lib.bitdrop_collapse_buffer.restype = ctypes.c_size_t

    def collapse_bytes(self, data: bytes) -> bytes:
        if not data:
            return b""

        size = len(data)

        in_buf = (ctypes.c_uint8 * size)(*data)
        out_payload = (ctypes.c_uint8 * size)()
        out_tags = (ctypes.c_uint8 * size)()
        collapse_count = ctypes.c_uint32(0)

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

        if written == 0:
            # Kernel failed; fall back to original data
            return data

        return bytes(out_payload[:written])
