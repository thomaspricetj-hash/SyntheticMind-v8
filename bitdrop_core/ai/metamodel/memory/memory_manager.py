from __future__ import annotations
from typing import List

from .memory_store import MemoryStore
from ..librarian_helper import LibrarianHelper
from ..bitdrop_manager import BitDropManager


class MemoryManager:
    """
    Thin manager over the strict M2 MemoryStore.

    Exposes:
        • remember(text)  -> store binary + signals (no text retained)
        • recall(query)   -> returns reconstructed texts via BitDrop
    """

    def __init__(self):
        helper = LibrarianHelper()
        bitdrop = BitDropManager()
        self.store = MemoryStore(helper, bitdrop)

    # ------------------------------------------------------------
    # WRITE MEMORY
    # ------------------------------------------------------------
    def remember(self, text: str):
        """
        Store a memory derived from raw text.
        Text is NOT stored; only signals + BitDrop binary are kept.
        """

        # Fast reject invalid input
        if not text or not isinstance(text, str):
            return None

        # Normalize without changing semantics
        cleaned = text.strip()
        if not cleaned:
            return None

        # Delegate to MemoryStore
        return self.store.write(cleaned)

    # ------------------------------------------------------------
    # READ MEMORY
    # ------------------------------------------------------------
    def recall(self, query: str, top_k: int = 3) -> List[str]:
        """
        Recall top_k memories relevant to the query.
        Returns reconstructed text strings (via BitDrop) only.
        """

        # Fast reject invalid input
        if not query or not isinstance(query, str):
            return []

        cleaned = query.strip()
        if not cleaned:
            return []

        # Retrieve items
        items = self.store.read(cleaned, top_k=top_k)

        # Expand (BitDrop decompress)
        expanded = self.store.expand_items_text(items)

        # Guarantee list[str]
        if not expanded:
            return []
        return expanded




