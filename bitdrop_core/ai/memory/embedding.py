# ai/memory/embedding.py

import json
import urllib.request
import urllib.error
import hashlib
import numpy as np


class EmbeddingEngine:
    """
    Hybrid embedding engine:
      • Uses Ollama (nomic-embed-text) when available
      • Falls back to a deterministic local embedding when offline
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
        """

        # Try Ollama first
        vec = self._try_ollama(text)
        if vec is not None:
            return vec

        # Fallback: deterministic local embedding
        return self._local_embed(text)

    # ------------------------------------------------------------
    # OLLAMA BACKEND
    # ------------------------------------------------------------
    def _try_ollama(self, text: str):
        payload = {
            "model": self.model,
            "prompt": text
        }

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

                # Validate schema
                emb = result.get("embedding")
                if not isinstance(emb, list):
                    return None

                # Convert to numpy + normalize
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
            return np.zeros(self.dim, dtype=np.float32)

        # Hash text into a deterministic seed
        h = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "little")

        rng = np.random.default_rng(seed)
        vec = rng.normal(0, 1, self.dim).astype(np.float32)

        return self._normalize(vec)

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------
    def _normalize(self, vec: np.ndarray):
        norm = np.linalg.norm(vec)
        if norm > 0:
            return vec / norm
        return vec
