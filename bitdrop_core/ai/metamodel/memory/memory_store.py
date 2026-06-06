from __future__ import annotations
from typing import Any

from .memory_item import MemoryItem
from .memory_index import MemoryIndex


class MemoryStore:
    """
    Strict M2 Memory Store:
        • NO text stored in memory items
        • NO chunks stored
        • embeddings + bloom + patterns
        • BitDrop binary as the ONLY stored representation
        • on-demand decompression from BitDrop binary
    """

    def __init__(self, helper, bitdrop):
        self.helper = helper
        self.bitdrop = bitdrop
        self.index = MemoryIndex()

    # ------------------------------------------------------------
    # WRITE MEMORY
    # ------------------------------------------------------------
    def write(self, text: str) -> MemoryItem:
        """
        Convert raw text into signals + BitDrop binary.
        Store only the compressed representation and search signals.
        """

        # Derive signals
        chunks = self.helper.chunk_text(text)
        embedding = self.helper.embed_text(text)
        bloom = self.helper.build_bloom(chunks)
        patterns = self.helper.extract_patterns(chunks)

        # Collapse to BitDrop binary
        binary = self.bitdrop.collapse_text(text)

        # Build memory item (strict M2: no raw text stored)
        item = MemoryItem(
            embedding=embedding,
            bloom=bloom,
            patterns=patterns,
            bitdrop_binary=binary,
        )

        # Add to index
        self.index.add(item)
        return item

    # ------------------------------------------------------------
    # READ MEMORY
    # ------------------------------------------------------------
    def read(self, query: str, top_k: int = 5):
        """
        Generate query signals and perform hybrid search.
        Returns MemoryItem objects (not text).
        """

        q_chunks = self.helper.chunk_text(query)
        q_embed = self.helper.embed_text(query)
        q_bloom = self.helper.build_bloom(q_chunks)
        q_patterns = self.helper.extract_patterns(q_chunks)

        return self.index.search(
            query_embedding=q_embed,
            query_bloom=q_bloom,
            query_patterns=q_patterns,
            top_k=top_k,
        )

    # ------------------------------------------------------------
    # DECOMPRESSOR
    # ------------------------------------------------------------
    def expand_item_text(self, item: MemoryItem) -> str:
        """
        Reconstruct text from BitDrop binary.
        """

        binary = getattr(item, "bitdrop_binary", None)
        if not binary:
            return ""

        return self.bitdrop.expand_text(binary)

    def expand_items_text(self, items) -> list[str]:
        """
        Expand a list of MemoryItem objects into reconstructed text.
        """
        return [self.expand_item_text(it) for it in items]





