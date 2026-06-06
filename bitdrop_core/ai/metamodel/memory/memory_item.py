from __future__ import annotations
from typing import List, Dict, Any
import time


class MemoryItem:
    """
    Strict M2 Memory Item:
        • NO raw text stored
        • NO chunks stored
        • embedding vector
        • bloom filter
        • pattern signature
        • bitdrop-collapsed binary (source of truth)
    """

    def __init__(
        self,
        embedding: List[float],
        bloom: set,
        patterns: Dict[str, Any],
        bitdrop_binary: bytes,
    ):
        # Core strict-M2 fields
        self.embedding = embedding
        self.bloom = bloom
        self.patterns = patterns

        # BitDrop binary is the ONLY stored representation
        self.bitdrop_binary = bitdrop_binary

        # Backward compatibility alias
        self.binary = bitdrop_binary

        # Timestamp for recency-based ranking or decay
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the item to a JSON-safe dictionary.
        """
        return {
            "embedding": self.embedding,
            "bloom": list(self.bloom),
            "patterns": self.patterns,
            "binary": self.bitdrop_binary.hex(),
            "timestamp": self.timestamp,
        }



