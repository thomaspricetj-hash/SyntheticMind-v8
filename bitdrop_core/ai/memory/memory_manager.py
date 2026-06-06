# ai/memory/memory_manager.py

from __future__ import annotations

from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .vector_store import VectorStore
from .embedding import EmbeddingEngine


class MemoryManager:
    """
    Unified cognitive memory system combining:
        • Episodic memory (chronological events)
        • Semantic memory (facts, key-value knowledge)
        • Vector memory (embedding-based retrieval)
    """

    def __init__(self, max_events: int = 5000):
        self.episodic = EpisodicMemory(max_events=max_events)
        self.semantic = SemanticMemory()
        self.vector = VectorStore()
        self.embedder = EmbeddingEngine()

        # Optional: cache embeddings to avoid recomputation
        self._embed_cache = {}

    # -------------------------------------------------------------
    # INTERNAL UTILITIES
    # -------------------------------------------------------------

    def _embed(self, text: str):
        """Cached embedding wrapper."""
        if text in self._embed_cache:
            return self._embed_cache[text]

        vec = self.embedder.embed(text)
        self._embed_cache[text] = vec
        return vec

    # -------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------

    def remember(self, text: str, event_type: str = "user_message"):
        """
        Store text in episodic + vector memory.
        Automatically deduplicates and normalizes.
        """

        if not text or not isinstance(text, str):
            return None

        # 1. Episodic memory (structured)
        episode = self.episodic.add(event_type, text)

        # 2. Vector memory
        vec = self._embed(text)
        self.vector.add(vec, text)

        return episode

    # -------------------------------------------------------------

    def recall(self, query: str, top_k: int = 5):
        """
        Semantic search over vector memory.
        Returns a list of {text, score}.
        """

        if not query:
            return []

        qvec = self._embed(query)
        results = self.vector.search(qvec, top_k=top_k)

        # Normalize output format
        return [
            {"text": text, "score": float(score)}
            for score, text in results
        ]

    # -------------------------------------------------------------

    def set_fact(self, key: str, value: str):
        """Store a semantic fact."""
        if key and value:
            self.semantic.set(key, value)

    def get_fact(self, key: str):
        """Retrieve a semantic fact."""
        return self.semantic.get(key)

    # -------------------------------------------------------------

    def summarize_recent(self, n: int = 5):
        """
        Returns a compact summary of the last N episodic events.
        Useful for context injection.
        """
        events = self.episodic.last(n)
        return [
            f"[{e['type']}] {e['payload']}"
            for e in events
        ]

    # -------------------------------------------------------------

    def clear(self):
        """Reset all memory subsystems."""
        self.episodic.clear()
        self.semantic.clear()
        self.vector.clear()
        self._embed_cache.clear()
