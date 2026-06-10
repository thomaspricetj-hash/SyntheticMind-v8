from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import urllib.request
import urllib.error
import hashlib
import numpy as np


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Embedding3D:
    """
    3D structural view of an embedding operation.

    axis_x: raw text
    axis_y: character-level decomposition
    axis_z: backend used, dim, norm, seed, stats
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# Global 3D state — must be declared BEFORE any function uses it
_last_3d: Optional[Embedding3D] = None


def _build_3d(text: str, vec: np.ndarray, backend: str,
              extra: Dict[str, Any] | None = None) -> Embedding3D:

    axis_z = {
        "backend": backend,
        "dim": len(vec),
        "norm": float(np.linalg.norm(vec)),
        "min": float(vec.min()) if vec.size else 0.0,
        "max": float(vec.max()) if vec.size else 0.0,
    }

    if extra:
        axis_z.update(extra)

    return Embedding3D(
        raw_text=text,
        axis_x=text,
        axis_y=list(text),
        axis_z=axis_z,
    )


# ============================================================
# HYBRID EMBEDDING ENGINE (3D‑MAX)
# ============================================================

class EmbeddingEngine:
    """
    Hybrid embedding engine (3D‑MAX):
      • Uses Ollama (nomic-embed-text) when available
      • Falls back to deterministic local embedding
      • Always produces a 3D structural envelope
    """

    def __init__(self, model="nomic-embed-text", dim=768):
        self.model = model
        self.dim = dim
        self.base = "http://127.0.0.1:11434"

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def embed(self, text: str):
        """
        Returns a vector embedding for the given text.
        Never throws — always returns a valid vector.
        Also stores a 3D structural envelope in `_last_3d`.
        """
        global _last_3d

        # Try Ollama first
        vec = self._try_ollama(text)
        if vec is not None:
            _last_3d = _build_3d(text, vec, backend="ollama")
            return vec

        # Fallback: deterministic local embedding
        vec, seed = self._local_embed(text)
        _last_3d = _build_3d(text, vec, backend="local", extra={"seed": seed})
        return vec

    # ------------------------------------------------------------
    # OLLAMA BACKEND
    # ------------------------------------------------------------
    def _try_ollama(self, text: str):
        payload = {"model": self.model, "prompt": text}
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base}/api/embeddings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                result = json.loads(resp.read().decode("utf-8"))

                emb = result.get("embedding")
                if not isinstance(emb, list):
                    return None

                vec = np.array(emb, dtype=np.float32)
                return self._normalize(vec)

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            return None
        except Exception:
            return None

    # ------------------------------------------------------------
    # LOCAL FALLBACK (deterministic, fast, offline)
    # ------------------------------------------------------------
    def _local_embed(self, text: str):
        if not text:
            return np.zeros(self.dim, dtype=np.float32), 0

        # Deterministic seed from SHA-256
        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "little")

        rng = np.random.default_rng(seed)
        vec = rng.normal(0, 1, self.dim).astype(np.float32)

        return self._normalize(vec), seed

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------
    def _normalize(self, vec: np.ndarray):
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


