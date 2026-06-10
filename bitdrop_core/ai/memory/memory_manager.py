from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Existing memory system (episodic, semantic, vector, embedding)
from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .vector_store import VectorStore
from .embedding import EmbeddingEngine

# Low‑level M2 memory structures
from bitdrop_core.ai.metamodel.memory.memory_index import MemoryIndex
from bitdrop_core.ai.metamodel.memory.memory_item import MemoryItem

# HYBRID COMPRESSOR (V2)
from bitdrop_core.ai.compression.bitdrop_collapse_codec import BitDropCollapseEngine



# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Memory3D:
    raw_input: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[Memory3D] = None


def _build_3d(raw: str, op: str, extra: Dict[str, Any] | None = None) -> Memory3D:
    axis_y = raw.split() if isinstance(raw, str) else [type(raw).__name__]
    axis_z = {"op": op}
    if extra:
        axis_z.update(extra)

    return Memory3D(
        raw_input=str(raw),
        axis_x=str(raw),
        axis_y=axis_y,
        axis_z=axis_z,
    )


# ============================================================
# MEMORY MANAGER (3D‑MAX + INDEX/STORE + HYBRID BITDROP)
# ============================================================

class MemoryManager:
    """
    Unified cognitive memory system combining:
        • Episodic memory
        • Semantic memory
        • Vector memory
        • KV store
        • Strict‑M2 MemoryStore + MemoryIndex
        • Hybrid BitDropCollapseEngineV2 for M2 bitdrop_binary
    """

    def __init__(self, max_events: int = 5000):

        # FIX: import MemoryStore here to avoid circular import
        from bitdrop_core.ai.metamodel.memory.memory_store import MemoryStore

        self.episodic = EpisodicMemory(max_events=max_events)
        self.semantic = SemanticMemory()
        self.vector = VectorStore()
        self.embedder = EmbeddingEngine()

        # Hybrid BitDrop collapse engine (V2)
        self.bitdrop = BitDropCollapseEngine()

        # Wire hybrid BitDrop into MemoryStore
        self.store = MemoryStore(helper=None, bitdrop=self.bitdrop)
        self.index = MemoryIndex()

        self._embed_cache: Dict[str, List[float]] = {}
        self._kv: Dict[str, str] = {}
        self._last_3d: Optional[Memory3D] = None

        self._bootstrap_from_store()

    # -------------------------------------------------------------
    # INTERNAL UTILITIES
    # -------------------------------------------------------------

    def _embed(self, text: str) -> List[float]:
        if text in self._embed_cache:
            return self._embed_cache[text]

        vec = self.embedder.embed(text)

        try:
            vec = list(map(float, vec))
        except Exception:
            vec = [float(x) for x in vec]

        self._embed_cache[text] = vec
        return vec

    def _bootstrap_from_store(self):
        try:
            items: List[MemoryItem] = self.store.load_all()
        except Exception:
            items = []

        for item in items:
            embedding = getattr(item, "embedding", None)
            if embedding:
                try:
                    emb = list(map(float, embedding))
                except Exception:
                    emb = [float(x) for x in embedding]
                self.vector.add(emb, "[m2]")

            try:
                self.index.add(item)
            except Exception:
                pass

    # -------------------------------------------------------------
    # STRICT‑M2 ITEM BUILDER
    # -------------------------------------------------------------

    def _build_m2_item(self, text: str, embedding: List[float]) -> MemoryItem:
        try:
            embedding = list(map(float, embedding))
        except Exception:
            embedding = [float(x) for x in embedding]

        bloom = {hash(tok) for tok in text.split()}

        patterns = {
            "len": len(text),
            "words": len(text.split()),
        }

        # FIXED — BitDrop V2 uses collapse(), not collapse_text()
        binary = self.bitdrop.collapse(text)

        # FIXED — MemoryItem requires bytes
        binary = binary.encode("utf-8")

        return MemoryItem(
            embedding=embedding,
            bloom=bloom,
            patterns=patterns,
            bitdrop_binary=binary,
        )

    # -------------------------------------------------------------
    # PUBLIC API — Episodic + Vector + Index/Store
    # -------------------------------------------------------------

    def remember(self, text: str, event_type: str = "user_message"):
        if not text or not isinstance(text, str):
            return None

        episode = self.episodic.add(event_type, text)

        vec = self._embed(text)
        self.vector.add(vec, text)

        item = self._build_m2_item(text, vec)

        try:
            self.store.save(item)
        except Exception:
            pass

        try:
            self.index.add(item)
        except Exception:
            pass

        self._last_3d = _build_3d(
            text,
            op="remember",
            extra={
                "event_type": event_type,
                "embedding_dim": len(vec),
                "episodic_index": len(self.episodic.timeline) - 1,
            },
        )

        return episode

    # -------------------------------------------------------------
    # FIXED RECALL — WORKS WITH DICTS, TUPLES, ANYTHING
    # AND RETURNS STRINGS (RUNTIME COMPATIBLE)
    # -------------------------------------------------------------

    def recall(self, query: str, top_k: int = 5):
        if not query:
            return []

        qvec = self._embed(query)

        vec_results = self.vector.search(qvec, top_k=top_k)

        vec_formatted = []

        for r in vec_results:
            if isinstance(r, dict):
                text = r.get("text", "[vector]")
                score = float(r.get("score", 0.0))
                vec_formatted.append({"text": text, "score": score})
                continue

            if isinstance(r, (tuple, list)) and len(r) >= 2:
                text = r[0]
                score = float(r[1])
                vec_formatted.append({"text": text, "score": score})
                continue

        idx_formatted = []
        try:
            idx_results = self.index.search(qvec, top_k=top_k)
            for r in idx_results:
                if isinstance(r, MemoryItem):
                    idx_formatted.append({"text": "[m2]", "score": 1.0})
        except Exception:
            pass

        merged: Dict[str, float] = {}
        for item in vec_formatted + idx_formatted:
            t = item["text"]
            s = item["score"]
            if t not in merged or s > merged[t]:
                merged[t] = s

        formatted = [
            {"text": t, "score": merged[t]}
            for t in sorted(merged, key=lambda x: merged[x], reverse=True)[:top_k]
        ]

        return [item["text"] for item in formatted]

    # -------------------------------------------------------------
    # SEMANTIC MEMORY
    # -------------------------------------------------------------

    def set_fact(self, key: str, value: str):
        self.semantic.set(key, value)
        self._last_3d = _build_3d(key, "set_fact", {"value": value})

    def get_fact(self, key: str):
        val = self.semantic.get(key)
        self._last_3d = _build_3d(key, "get_fact", {"value": val})
        return val

    # -------------------------------------------------------------
    # KV STORE
    # -------------------------------------------------------------

    def write(self, key: str, value: str):
        self._kv[key] = value
        self._last_3d = _build_3d(key, "kv_write", {"value": value})

    def read(self, key: str):
        val = self._kv.get(key)
        self._last_3d = _build_3d(key, "kv_read", {"value": val})
        return val

    def delete(self, key: str):
        existed = key in self._kv
        if existed:
            del self._kv[key]
        self._last_3d = _build_3d(key, "kv_delete", {"existed": existed})
        return existed

    def exists(self, key: str) -> bool:
        exists = key in self._kv
        self._last_3d = _build_3d(key, "kv_exists", {"exists": exists})
        return exists

    def list_keys(self):
        keys = list(self._kv.keys())
        self._last_3d = _build_3d("list_keys", "kv_list_keys", {"keys": keys})
        return keys

    # -------------------------------------------------------------
    # UTILITIES
    # -------------------------------------------------------------

    def summarize_recent(self, n: int = 5):
        events = self.episodic.last(n)
        summary = [f"[{e['type']}] {e['payload']}" for e in events]
        self._last_3d = _build_3d("summarize_recent", "summarize_recent", {"n": n})
        return summary

    def clear(self):
        self.episodic.clear()
        self.semantic.clear()
        self.vector.clear()
        self._embed_cache.clear()
        self._kv.clear()

        try:
            self.store.clear()
        except Exception:
            pass

        try:
            self.index.clear()
        except Exception:
            pass

        self._last_3d = _build_3d("clear", "clear", {"status": "all memory cleared"})




