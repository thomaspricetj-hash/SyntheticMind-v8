from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math
import time


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class VectorStore3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# HYBRID VECTOR STORE — RAW + COLLAPSED + 3D‑MAX
# ============================================================

class VectorStore:
    """
    Hybrid vector store.

    Stores:
        • raw text embeddings
        • collapsed (BitDrop) text embeddings
        • labels / payloads
        • 3D‑MAX telemetry

    Search:
        • cosine similarity
        • hybrid scoring (raw + collapsed)
    """

    def __init__(self):
        self._items: List[Dict[str, Any]] = []
        self._last_3d: Optional[VectorStore3D] = None

    # ------------------------------------------------------------
    # ADD
    # ------------------------------------------------------------
    def add(self, embedding: List[float], text: str, *, collapsed: Optional[str] = None):
        """
        Add a vector entry.

        embedding: raw text embedding
        text: raw text
        collapsed: optional collapsed text (BitDrop)
        """
        item = {
            "embedding": embedding,
            "text": text,
            "collapsed": collapsed,
        }
        self._items.append(item)

        self._last_3d = VectorStore3D(
            axis_x="add",
            axis_y=[f"total_items:{len(self._items)}"],
            axis_z={
                "embedding_dim": len(embedding),
                "has_collapsed": collapsed is not None,
            },
        )

    # ------------------------------------------------------------
    # CLEAR
    # ------------------------------------------------------------
    def clear(self):
        self._items.clear()
        self._last_3d = VectorStore3D(
            axis_x="clear",
            axis_y=["total_items:0"],
            axis_z={"status": "cleared"},
        )

    # ------------------------------------------------------------
    # SEARCH (HYBRID)
    # ------------------------------------------------------------
    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search:
            70% raw embedding similarity
            30% collapsed embedding similarity (if available)
        """

        start = time.time()
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for item in self._items:
            base = self._cosine_similarity(query_embedding, item["embedding"])

            # collapsed similarity placeholder (can be extended if you store collapsed embeddings)
            collapsed_score = 0.0

            score = 0.70 * base + 0.30 * collapsed_score
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [it for _, it in scored[:top_k]]

        latency = int((time.time() - start) * 1000)

        self._last_3d = VectorStore3D(
            axis_x="search",
            axis_y=[
                f"items:{len(self._items)}",
                f"top_k:{top_k}",
                f"returned:{len(results)}",
            ],
            axis_z={"latency_ms": latency},
        )

        # runtime‑compatible format
        formatted = []
        for item in results:
            formatted.append(
                {
                    "text": item["text"],
                    "score": 1.0,  # you can expose actual score if needed
                }
            )

        return formatted

    # ------------------------------------------------------------
    # COSINE
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





