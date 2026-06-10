from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math
import time


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class M2Index3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# MEMORY INDEX — STRICT M2 + HYBRID + 3D‑MAX
# ============================================================

class MemoryIndex:
    """
    Hybrid‑aware M2 memory index (3D‑MAX Edition).

    Supports:
        • embedding similarity (cosine)
        • bloom filter overlap
        • pattern signature overlap
        • bitdrop_binary length similarity (hybrid)
        • top‑k ranking
        • deterministic scoring
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.items: List[Any] = []
        self._last_3d: Optional[M2Index3D] = None

    # ------------------------------------------------------------
    # ADD ITEM
    # ------------------------------------------------------------
    def add(self, item):
        """
        Add a MemoryItem to the index.
        """
        self.items.append(item)

        # 3D‑MAX telemetry
        self._last_3d = M2Index3D(
            axis_x="add",
            axis_y=[f"total_items:{len(self.items)}"],
            axis_z={"ok": True},
        )

    # ------------------------------------------------------------
    # SEARCH (HYBRID)
    # ------------------------------------------------------------
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Any]:
        """
        Hybrid scoring:
            60% embedding similarity
            20% bloom overlap
            10% pattern signature overlap
            10% bitdrop_binary length similarity
        """

        start = time.time()
        scored = []

        # Build hybrid query signals
        query_bloom = {hash(tok) for tok in " ".join(map(str, query_embedding)).split()}
        query_patterns = {
            "len": len(query_embedding),
            "words": len(query_embedding),
        }

        for item in self.items:
            score = (
                0.60 * self._cosine_similarity(query_embedding, item.embedding)
                + 0.20 * self._bloom_overlap(query_bloom, item.bloom)
                + 0.10 * self._pattern_overlap(query_patterns, item.patterns)
                + 0.10 * self._bitdrop_similarity(item)
            )
            scored.append((score, item))

        # Deterministic sort
        scored.sort(key=lambda x: x[0], reverse=True)

        # Clamp top‑k
        results = [it for _, it in scored[:top_k]]

        latency = int((time.time() - start) * 1000)

        # 3D‑MAX telemetry
        self._last_3d = M2Index3D(
            axis_x="search",
            axis_y=[
                f"items:{len(self.items)}",
                f"top_k:{top_k}",
                f"returned:{len(results)}",
            ],
            axis_z={"latency_ms": latency},
        )

        return results

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

    # ------------------------------------------------------------
    # HYBRID BITDROP SIMILARITY
    # ------------------------------------------------------------
    def _bitdrop_similarity(self, item) -> float:
        """
        Compare bitdrop_binary lengths.
        Shorter difference → higher similarity.
        """
        try:
            length = len(item.bitdrop_binary)
        except Exception:
            return 0.0

        # Normalize length similarity
        # 0 difference → 1.0 score
        # large difference → lower score
        diff = abs(length - 1024)  # 1024 = neutral reference
        return max(0.0, 1.0 - (diff / 4096))





