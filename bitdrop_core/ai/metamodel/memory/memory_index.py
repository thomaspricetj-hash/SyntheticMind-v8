from __future__ import annotations
from typing import List, Dict, Any
import math


class MemoryIndex:
    """
    Lightweight M2 memory index.

    Supports:
        • embedding similarity (cosine)
        • bloom filter overlap
        • pattern signature overlap
        • top‑k ranking
    """

    def __init__(self):
        self.items: List[Any] = []

    # ------------------------------------------------------------
    # ADD ITEM
    # ------------------------------------------------------------
    def add(self, item):
        """
        Add a MemoryItem to the index.
        """
        self.items.append(item)

    # ------------------------------------------------------------
    # SEARCH
    # ------------------------------------------------------------
    def search(
        self,
        query_embedding: List[float],
        query_bloom: set,
        query_patterns: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Any]:
        """
        Rank items using hybrid scoring:
            60% embedding similarity
            25% bloom overlap
            15% pattern signature overlap
        """

        scored = []
        for item in self.items:
            score = (
                0.60 * self._cosine_similarity(query_embedding, item.embedding)
                + 0.25 * self._bloom_overlap(query_bloom, item.bloom)
                + 0.15 * self._pattern_overlap(query_patterns, item.patterns)
            )
            scored.append((score, item))

        # Sort by descending score
        scored.sort(key=lambda x: x[0], reverse=True)

        return [it for _, it in scored[:top_k]]

    # ------------------------------------------------------------
    # SIMILARITY METRICS
    # ------------------------------------------------------------
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))

        if na == 0.0 or nb == 0.0:
            return 0.0

        return dot / (na * nb)

    def _bloom_overlap(self, q: set, m: set) -> float:
        if not q or not m:
            return 0.0

        inter = len(q & m)
        return inter / max(1, len(q))

    def _pattern_overlap(self, q: Dict[str, Any], m: Dict[str, Any]) -> float:
        if not q or not m:
            return 0.0

        matches = 0
        total = len(q)

        for k, v in q.items():
            if k in m and m[k] == v:
                matches += 1

        return matches / max(1, total)




