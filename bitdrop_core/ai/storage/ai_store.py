from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

import numpy as np

from bitdrop_core.ai.persistence.tiered_kv import TieredKV
from bitdrop_core.ai.persistence.dataset_store import DatasetStore

from .vector_index import VectorIndex


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class AIStore3D:
    axis_x: str
    axis_y: list
    axis_z: dict


_EMB_SUFFIX = b":emb"
_EMB_META_SUFFIX = b":emb_meta"
_COMPLETION_PREFIX = b"completion:"


# ============================================================
# AIStore — MAX SPEED + 3D‑MAX
# ============================================================

class AIStore:
    """
    Unified high-performance storage layer for the AI system (3D‑MAX Edition).

    Responsibilities:
        - Document storage (TieredKV, in-memory)
        - Embedding storage:
            * raw in VectorIndex (fast search)
            * binary payload + metadata in TieredKV
        - Completion caching (in-memory dedup + TieredKV)
        - Interaction logging (DatasetStore, in-memory)
        - Repair stub (no-op, fast)
        - 3D‑MAX telemetry for all major operations
    """

    def __init__(self, root_path: str):
        self.root_path = root_path
        os.makedirs(self.root_path, exist_ok=True)

        self.docs_path = os.path.join(self.root_path, "docs")
        self.logs_path = os.path.join(self.root_path, "logs")
        self.cache_path = os.path.join(self.root_path, "cache")
        self.emb_path = os.path.join(self.root_path, "embeddings")

        for p in (self.docs_path, self.logs_path, self.cache_path, self.emb_path):
            os.makedirs(p, exist_ok=True)

        # Core storage engines
        self.kv = TieredKV()
        self.logger = DatasetStore()
        self.index = VectorIndex(os.path.join(self.emb_path, "index"))

        # Completion dedup
        self._completion_fps = set()

        # 3D‑MAX telemetry
        self._last_3d: Optional[AIStore3D] = None

    # ---------------------------------------------------------
    # Document storage
    # ---------------------------------------------------------
    def put_doc(self, key: bytes, value: bytes) -> None:
        start = time.time()
        self.kv.set(key, value)

        self._last_3d = AIStore3D(
            axis_x="put_doc",
            axis_y=[f"key_len:{len(key)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    def get_doc(self, key: bytes) -> Optional[bytes]:
        start = time.time()
        value = self.kv.get(key)

        self._last_3d = AIStore3D(
            axis_x="get_doc",
            axis_y=[f"key_len:{len(key)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "found": value is not None,
            },
        )
        return value

    def has_doc(self, key: bytes) -> bool:
        start = time.time()
        exists = self.kv.has(key)

        self._last_3d = AIStore3D(
            axis_x="has_doc",
            axis_y=[f"key_len:{len(key)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "exists": exists,
            },
        )
        return exists

    def delete_doc(self, key: bytes) -> None:
        start = time.time()
        self.kv.delete(key)

        self._last_3d = AIStore3D(
            axis_x="delete_doc",
            axis_y=[f"key_len:{len(key)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    # ---------------------------------------------------------
    # Embedding storage (raw + KV)
    # ---------------------------------------------------------
    def _emb_key(self, doc_id: bytes) -> bytes:
        return doc_id + _EMB_SUFFIX

    def _emb_meta_key(self, doc_id: bytes) -> bytes:
        return doc_id + _EMB_META_SUFFIX

    def put_embedding(
        self,
        doc_id: bytes,
        vector: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:

        start = time.time()

        vec32 = vector.astype(np.float32, copy=False)

        # Raw vector → vector index
        self.index.add(doc_id, vec32)

        # Binary payload + metadata → KV
        payload = vec32.tobytes()
        meta_bytes = json.dumps(metadata or {}).encode("utf-8")

        self.kv.set(self._emb_key(doc_id), payload)
        self.kv.set(self._emb_meta_key(doc_id), meta_bytes)

        self._last_3d = AIStore3D(
            axis_x="put_embedding",
            axis_y=[f"doc_id_len:{len(doc_id)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "vec_dim": len(vec32),
                "has_meta": metadata is not None,
            },
        )

    def get_embedding(self, doc_id: bytes) -> Optional[Tuple[np.ndarray, Dict[str, Any]]]:
        start = time.time()

        payload = self.kv.get(self._emb_key(doc_id))
        meta_bytes = self.kv.get(self._emb_meta_key(doc_id))

        if payload is None or meta_bytes is None:
            self._last_3d = AIStore3D(
                axis_x="get_embedding",
                axis_y=[f"doc_id_len:{len(doc_id)}"],
                axis_z={
                    "latency_ms": int((time.time() - start) * 1000),
                    "found": False,
                },
            )
            return None

        vec = np.frombuffer(payload, dtype=np.float32)
        metadata = json.loads(meta_bytes.decode("utf-8"))

        self._last_3d = AIStore3D(
            axis_x="get_embedding",
            axis_y=[f"doc_id_len:{len(doc_id)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "found": True,
                "vec_dim": len(vec),
            },
        )

        return vec, metadata

    def search_embeddings(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[bytes, float]]:
        start = time.time()
        results = self.index.search(query_vector, top_k=top_k)

        self._last_3d = AIStore3D(
            axis_x="search_embeddings",
            axis_y=[f"top_k:{top_k}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "returned": len(results),
            },
        )

        return results

    # ---------------------------------------------------------
    # Completion cache
    # ---------------------------------------------------------
    def cache_completion(self, fingerprint: bytes, payload: bytes) -> None:
        start = time.time()

        self._completion_fps.add(fingerprint)
        key = _COMPLETION_PREFIX + fingerprint
        self.kv.set(key, payload)

        self._last_3d = AIStore3D(
            axis_x="cache_completion",
            axis_y=[f"fp_len:{len(fingerprint)}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    def get_cached_completion(self, fingerprint: bytes) -> Optional[bytes]:
        start = time.time()

        if fingerprint not in self._completion_fps:
            self._last_3d = AIStore3D(
                axis_x="get_cached_completion",
                axis_y=[f"fp_len:{len(fingerprint)}"],
                axis_z={"latency_ms": int((time.time() - start) * 1000), "found": False},
            )
            return None

        key = _COMPLETION_PREFIX + fingerprint
        payload = self.kv.get(key)

        self._last_3d = AIStore3D(
            axis_x="get_cached_completion",
            axis_y=[f"fp_len:{len(fingerprint)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "found": payload is not None,
            },
        )

        return payload

    # ---------------------------------------------------------
    # Interaction logging
    # ---------------------------------------------------------
    def log_interaction(
        self,
        user_id: str,
        prompt: str,
        response: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:

        start = time.time()

        record = {
            "ts": time.time(),
            "user_id": user_id,
            "prompt": prompt,
            "response": response,
            "meta": meta or {},
        }

        self.logger.add("interactions", record)

        self._last_3d = AIStore3D(
            axis_x="log_interaction",
            axis_y=[f"user:{user_id}"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

    # ---------------------------------------------------------
    # Maintenance / repair
    # ---------------------------------------------------------
    def run_repair(self) -> List[Dict[str, Any]]:
        start = time.time()

        # No-op for MAX SPEED
        self._last_3d = AIStore3D(
            axis_x="run_repair",
            axis_y=["noop"],
            axis_z={"latency_ms": int((time.time() - start) * 1000)},
        )

        return []



