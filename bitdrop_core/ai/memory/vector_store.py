# ai/memory/vector_store.py

from __future__ import annotations
from typing import Dict, Any, List, Tuple
import uuid
import math
import time
import traceback


class VectorStore:
    """
    Production-grade in-memory vector store.

    Features:
        • structured envelopes
        • safe add/query
        • deterministic cosine similarity
        • metadata preservation
        • top-k clamping
        • malformed-vector protection
        • latency measurement
        • future-proof backend swap
        • MemoryManager-compatible search()
    """

    def __init__(self):
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: SAFE COSINE SIMILARITY
    # ------------------------------------------------------------
    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0

        dot = 0.0
        na = 0.0
        nb = 0.0

        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y

        if na <= 0.0 or nb <= 0.0:
            return 0.0

        return dot / (math.sqrt(na) * math.sqrt(nb))

    # ------------------------------------------------------------
    # ADD VECTOR
    # ------------------------------------------------------------
    def add(self, vector: List[float], metadata: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()

        try:
            if not isinstance(vector, list) or not all(isinstance(x, (int, float)) for x in vector):
                raise ValueError("invalid vector format")

            vid = str(uuid.uuid4())
            self.vectors[vid] = vector
            self.metadata[vid] = metadata or {}

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "id": vid,
                "vector_dim": len(vector),
                "metadata": metadata,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "id": None,
                "vector_dim": 0,
                "metadata": metadata,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # QUERY TOP-K
    # ------------------------------------------------------------
    def query(self, vector: List[float], top_k: int = 5) -> Dict[str, Any]:
        start = time.time()

        try:
            if top_k <= 0:
                top_k = 1

            if not isinstance(vector, list) or not all(isinstance(x, (int, float)) for x in vector):
                raise ValueError("invalid query vector")

            scored = []

            for vid, stored_vec in self.vectors.items():
                score = self._cosine(vector, stored_vec)
                scored.append({
                    "id": vid,
                    "score": score,
                    "metadata": self.metadata.get(vid, {}),
                })

            scored.sort(key=lambda x: x["score"], reverse=True)
            results = scored[:top_k]

            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "query_dim": len(vector),
                "top_k": top_k,
                "results": results,
                "count": len(results),
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "query_dim": len(vector) if isinstance(vector, list) else 0,
                "top_k": top_k,
                "results": [],
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # REQUIRED BY MemoryManager: search()
    # ------------------------------------------------------------
    def search(self, vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        MemoryManager expects search() to return a LIST of items,
        not a structured envelope. So we unwrap query().
        """
        q = self.query(vector, top_k=top_k)

        if not q.get("ok"):
            return []

        return q["results"]




