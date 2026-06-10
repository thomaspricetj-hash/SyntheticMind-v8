from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time
import traceback

from .memory_store import MemoryStore
from ..librarian_helper import LibrarianHelper
from ..bitdrop_manager import BitDropManager


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class M2Mgr3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# MEMORY MANAGER — STRICT M2 + 3D‑MAX
# ============================================================

class MemoryManager:
    """
    Thin manager over the strict M2 MemoryStore (3D‑MAX Edition).

    Exposes:
        • remember(text)  -> store binary + signals (no text retained)
        • recall(query)   -> returns reconstructed texts via BitDrop
    """

    def __init__(self):
        helper = LibrarianHelper()
        bitdrop = BitDropManager()
        self.store = MemoryStore(helper, bitdrop)
        self._last_3d: Optional[M2Mgr3D] = None

    # ------------------------------------------------------------
    # WRITE MEMORY
    # ------------------------------------------------------------
    def remember(self, text: str):
        """
        Store a memory derived from raw text.
        Text is NOT stored; only signals + BitDrop binary are kept.
        """

        start = time.time()

        # Fast reject invalid input
        if not text or not isinstance(text, str):
            self._last_3d = M2Mgr3D(
                axis_x="remember",
                axis_y=["invalid_input"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return None

        cleaned = text.strip()
        if not cleaned:
            self._last_3d = M2Mgr3D(
                axis_x="remember",
                axis_y=["empty_after_strip"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return None

        # Delegate to MemoryStore
        try:
            item = self.store.write(cleaned)

            # 3D‑MAX telemetry
            self._last_3d = M2Mgr3D(
                axis_x="remember",
                axis_y=[f"text_len:{len(cleaned)}"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "ok": True,
                },
            )

            return item

        except Exception as e:
            self._last_3d = M2Mgr3D(
                axis_x="remember",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "error": str(e),
                },
            )
            return None

    # ------------------------------------------------------------
    # READ MEMORY
    # ------------------------------------------------------------
    def recall(self, query: str, top_k: int = 3) -> List[str]:
        """
        Recall top_k memories relevant to the query.
        Returns reconstructed text strings (via BitDrop) only.
        """

        start = time.time()

        # Fast reject invalid input
        if not query or not isinstance(query, str):
            self._last_3d = M2Mgr3D(
                axis_x="recall",
                axis_y=["invalid_input"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return []

        cleaned = query.strip()
        if not cleaned:
            self._last_3d = M2Mgr3D(
                axis_x="recall",
                axis_y=["empty_after_strip"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return []

        try:
            # Retrieve items
            items = self.store.read(cleaned, top_k=top_k)

            # Expand (BitDrop decompress)
            expanded = self.store.expand_items_text(items)
            expanded = expanded or []

            # 3D‑MAX telemetry
            self._last_3d = M2Mgr3D(
                axis_x="recall",
                axis_y=[
                    f"query_len:{len(cleaned)}",
                    f"items:{len(items)}",
                    f"expanded:{len(expanded)}",
                ],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "ok": True,
                },
            )

            return expanded

        except Exception as e:
            self._last_3d = M2Mgr3D(
                axis_x="recall",
                axis_y=["exception"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "error": str(e),
                },
            )
            return []




