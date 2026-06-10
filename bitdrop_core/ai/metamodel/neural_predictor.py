from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


__all__ = ["PredictorOutput", "NeuralPredictor"]


@dataclass
class PredictorOutput:
    graph: Optional[str]
    backend: Optional[str]
    block_scale: float
    prefer_motif: bool
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeuralPredictor:
    """
    NeuralPredictor v8 — GPU‑aware, helper‑mesh‑aware, SyntheticMind‑compatible.

    Design goals:
    - Backward compatible with v6/v7 feature schema.
    - Pure‑Python CPU path (no hard dependency on GPU libs).
    - Optional GPU acceleration (Numba/CUDA) when available and enabled.
    - Stable, deterministic scoring for the same feature set.
    - Friendly to helper_mesh / BitDrop / compression pipeline.

    Features expected (backward compatible):
        entropy, entropy_norm, zero_ratio, match4, match4_norm,
        delta4_score, binary_strength, chunk_len,
        ascii_ratio, brace_ratio, kind_bonus,
        semantic_kind, shape, backend_hint,
        block_index, total_blocks, file_size
    """

    VERSION = "v8.0"

    def __init__(
        self,
        helper_manager: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.helper = helper_manager
        self.config: Dict[str, Any] = config or {}

        # Core weights (tunable; can be adapted by higher‑level trainer)
        self.weights: Dict[str, float] = {
            "entropy_norm": -0.70,
            "zero_ratio": 0.55,
            "match4_norm": 0.85,
            "delta4_score": 0.65,
            "binary_strength": 0.40,
            "ascii_ratio": 0.45,
            "brace_ratio": 0.55,
            "kind_bonus": 0.50,
            "chunk_len": 0.0000015,
        }

        # Thresholds (structure + motif bias)
        self.thresholds: Dict[str, float] = {
            "high_structure": 0.82,
            "medium_structure": 0.45,
            "motif_prefer": 0.72,
        }

        # Config overrides (for tuning without code changes)
        self._apply_config_overrides()

        # GPU acceleration flag (soft‑optional)
        self.use_gpu: bool = bool(self.config.get("use_gpu", False))
        self._gpu_enabled: bool = False
        if self.use_gpu:
            self._gpu_enabled = self._try_enable_gpu()

    # ---------------------------------------------------------
    # Config overrides
    # ---------------------------------------------------------
    def _apply_config_overrides(self) -> None:
        w_cfg = self.config.get("weights", {})
        t_cfg = self.config.get("thresholds", {})

        for k, v in w_cfg.items():
            if k in self.weights:
                self.weights[k] = float(v)

        for k, v in t_cfg.items():
            if k in self.thresholds:
                self.thresholds[k] = float(v)

    def _try_enable_gpu(self) -> bool:
        try:
            import numba  # noqa: F401
            from numba import cuda  # noqa: F401

            # Simple probe to ensure CUDA is available
            try:
                cuda.current_context()
            except Exception:
                # If context fails, keep GPU disabled
                return False
            return True
        except Exception:
            return False

    # ---------------------------------------------------------
    # Feature builder (backward compatible + new fields)
    # ---------------------------------------------------------
    def build_features(
        self,
        entropy: float,
        zero_ratio: float,
        match4: float,
        chunk_len: int,
        semantic_kind: str,
        block_index: int,
        total_blocks: int,
        ascii_ratio: float = 0.0,
        brace_ratio: float = 0.0,
        file_size: int = 0,
        entropy_norm: Optional[float] = None,
        match4_norm: Optional[float] = None,
        delta4_score: float = 0.0,
        binary_strength: float = 0.0,
        shape: Optional[str] = None,
        backend_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a feature dict compatible with predict().

        This is safe to call from BitDrop, helper_mesh, or compression
        engines that only know the older v5/v6 schema.
        """

        if entropy_norm is None:
            entropy_norm = entropy / 8.0
        if match4_norm is None:
            match4_norm = match4 / 10.0

        kind_bonus = 0.0
        if semantic_kind == "json":
            kind_bonus = 0.45
        elif semantic_kind == "text":
            kind_bonus = 0.30
        elif semantic_kind == "binary":
            kind_bonus = 0.15

        return {
            "entropy": float(entropy),
            "entropy_norm": float(entropy_norm),
            "zero_ratio": float(zero_ratio),
            "match4": float(match4),
            "match4_norm": float(match4_norm),
            "delta4_score": float(delta4_score),
            "binary_strength": float(binary_strength),
            "chunk_len": int(chunk_len),
            "ascii_ratio": float(ascii_ratio),
            "brace_ratio": float(brace_ratio),
            "kind_bonus": kind_bonus,
            "semantic_kind": semantic_kind,
            "shape": shape,
            "backend_hint": backend_hint,
            "block_index": int(block_index),
            "total_blocks": int(total_blocks),
            "file_size": int(file_size),
        }

    # ---------------------------------------------------------
    # Core scoring logic (CPU or GPU)
    # ---------------------------------------------------------
    def _structure_score(self, f: Dict[str, Any]) -> float:
        """
        Compute a normalized structure score in [0, 1].

        Deterministic for a given feature set and weight config.
        """

        # GPU path (optional, soft‑fail)
        if self._gpu_enabled:
            try:
                return self._gpu_score(f)
            except Exception:
                # Fall back to CPU if GPU path fails
                pass

        # CPU path
        w = self.weights
        score = 0.0
        score += f["entropy_norm"] * w["entropy_norm"]
        score += f["zero_ratio"] * w["zero_ratio"]
        score += f["match4_norm"] * w["match4_norm"]
        score += f["delta4_score"] * w["delta4_score"]
        score += f["binary_strength"] * w["binary_strength"]
        score += f["ascii_ratio"] * w["ascii_ratio"]
        score += f["brace_ratio"] * w["brace_ratio"]
        score += f["chunk_len"] * w["chunk_len"]
        score += f["kind_bonus"]

        # Slightly favor earlier blocks to bias toward header/metadata
        tb = max(f["total_blocks"], 1)
        pos_factor = 1.0 - (f["block_index"] / tb) * 0.05
        score *= pos_factor

        # Sigmoid normalization
        return 1.0 / (1.0 + math.exp(-score))



import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, List, Tuple


__all__ = ["PredictorOutput", "NeuralPredictor"]


@dataclass
class PredictorOutput:
    graph: Optional[str]
    backend: Optional[str]
    block_scale: float
    prefer_motif: bool
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class NeuralPredictor:
    """
    NeuralPredictor v8 — GPU‑aware, helper‑mesh‑aware, SyntheticMind‑compatible, 3D‑max.

    Design goals:
    - Backward compatible with v6/v7 feature schema.
    - Pure‑Python CPU path (no hard dependency on GPU libs).
    - Optional GPU acceleration (Numba/CUDA) when available and enabled.
    - Stable, deterministic scoring for the same feature set.
    - Friendly to helper_mesh / BitDrop / compression pipeline.
    - 1D, batch, and 3D tensor-style prediction APIs.

    Features expected (backward compatible):
        entropy, entropy_norm, zero_ratio, match4, match4_norm,
        delta4_score, binary_strength, chunk_len,
        ascii_ratio, brace_ratio, kind_bonus,
        semantic_kind, shape, backend_hint,
        block_index, total_blocks, file_size
    """

    VERSION = "v8.1-3dmax"

    def __init__(
        self,
        helper_manager: Any = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.helper = helper_manager
        self.config: Dict[str, Any] = config or {}

        # Core weights (tunable; can be adapted by higher‑level trainer)
        self.weights: Dict[str, float] = {
            "entropy_norm": -0.70,
            "zero_ratio": 0.55,
            "match4_norm": 0.85,
            "delta4_score": 0.65,
            "binary_strength": 0.40,
            "ascii_ratio": 0.45,
            "brace_ratio": 0.55,
            "kind_bonus": 0.50,
            "chunk_len": 0.0000015,
        }

        # Thresholds (structure + motif bias)
        self.thresholds: Dict[str, float] = {
            "high_structure": 0.82,
            "medium_structure": 0.45,
            "motif_prefer": 0.72,
        }

        # Config overrides (for tuning without code changes)
        self._apply_config_overrides()

        # GPU acceleration flag (soft‑optional)
        self.use_gpu: bool = bool(self.config.get("use_gpu", False))
        self._gpu_enabled: bool = False
        if self.use_gpu:
            self._gpu_enabled = self._try_enable_gpu()

        # Lightweight score cache (for repeated feature patterns)
        self._score_cache: Dict[Tuple[Any, ...], float] = {}
        self._score_cache_max: int = int(self.config.get("score_cache_max", 4096))

    # ---------------------------------------------------------
    # Config overrides
    # ---------------------------------------------------------
    def _apply_config_overrides(self) -> None:
        w_cfg = self.config.get("weights", {})
        t_cfg = self.config.get("thresholds", {})

        for k, v in w_cfg.items():
            if k in self.weights:
                self.weights[k] = float(v)

        for k, v in t_cfg.items():
            if k in self.thresholds:
                self.thresholds[k] = float(v)

    def _try_enable_gpu(self) -> bool:
        try:
            import numba  # noqa: F401
            from numba import cuda  # noqa: F401

            try:
                cuda.current_context()
            except Exception:
                return False
            return True
        except Exception:
            return False

    # ---------------------------------------------------------
    # Feature builder (backward compatible + new fields)
    # ---------------------------------------------------------
    def build_features(
        self,
        entropy: float,
        zero_ratio: float,
        match4: float,
        chunk_len: int,
        semantic_kind: str,
        block_index: int,
        total_blocks: int,
        ascii_ratio: float = 0.0,
        brace_ratio: float = 0.0,
        file_size: int = 0,
        entropy_norm: Optional[float] = None,
        match4_norm: Optional[float] = None,
        delta4_score: float = 0.0,
        binary_strength: float = 0.0,
        shape: Optional[str] = None,
        backend_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a feature dict compatible with predict().

        This is safe to call from BitDrop, helper_mesh, or compression
        engines that only know the older v5/v6 schema.
        """
        if entropy_norm is None:
            entropy_norm = entropy / 8.0
        if match4_norm is None:
            match4_norm = match4 / 10.0

        kind_bonus = 0.0
        if semantic_kind == "json":
            kind_bonus = 0.45
        elif semantic_kind == "text":
            kind_bonus = 0.30
        elif semantic_kind == "binary":
            kind_bonus = 0.15

        return {
            "entropy": float(entropy),
            "entropy_norm": float(entropy_norm),
            "zero_ratio": float(zero_ratio),
            "match4": float(match4),
            "match4_norm": float(match4_norm),
            "delta4_score": float(delta4_score),
            "binary_strength": float(binary_strength),
            "chunk_len": int(chunk_len),
            "ascii_ratio": float(ascii_ratio),
            "brace_ratio": float(brace_ratio),
            "kind_bonus": kind_bonus,
            "semantic_kind": semantic_kind,
            "shape": shape,
            "backend_hint": backend_hint,
            "block_index": int(block_index),
            "total_blocks": int(total_blocks),
            "file_size": int(file_size),
        }

    # ---------------------------------------------------------
    # Internal: cache key + score caching
    # ---------------------------------------------------------
    def _score_key(self, f: Dict[str, Any]) -> Tuple[Any, ...]:
        return (
            round(float(f["entropy_norm"]), 6),
            round(float(f["zero_ratio"]), 6),
            round(float(f["match4_norm"]), 6),
            round(float(f["delta4_score"]), 6),
            round(float(f["binary_strength"]), 6),
            round(float(f["ascii_ratio"]), 6),
            round(float(f["brace_ratio"]), 6),
            round(float(f["chunk_len"]), 0),
            round(float(f["kind_bonus"]), 6),
            f.get("semantic_kind", "unknown"),
            f.get("shape", None),
            f.get("backend_hint", None),
            int(f.get("block_index", 0)),
            int(f.get("total_blocks", 1)),
            int(f.get("file_size", 0)),
        )

    def _cache_score(self, key: Tuple[Any, ...], score: float) -> None:
        if len(self._score_cache) >= self._score_cache_max:
            self._score_cache.clear()
        self._score_cache[key] = score

    # ---------------------------------------------------------
    # Core scoring logic (CPU or GPU)
    # ---------------------------------------------------------
    def _structure_score(self, f: Dict[str, Any]) -> float:
        """
        Compute a normalized structure score in [0, 1].

        Deterministic for a given feature set and weight config.
        """
        key = self._score_key(f)
        cached = self._score_cache.get(key)
        if cached is not None:
            return cached

        if self._gpu_enabled:
            try:
                score = self._gpu_score(f)
                self._cache_score(key, score)
                return score
            except Exception:
                pass

        w = self.weights
        score = 0.0
        score += f["entropy_norm"] * w["entropy_norm"]
        score += f["zero_ratio"] * w["zero_ratio"]
        score += f["match4_norm"] * w["match4_norm"]
        score += f["delta4_score"] * w["delta4_score"]
        score += f["binary_strength"] * w["binary_strength"]
        score += f["ascii_ratio"] * w["ascii_ratio"]
        score += f["brace_ratio"] * w["brace_ratio"]
        score += f["chunk_len"] * w["chunk_len"]
        score += f["kind_bonus"]

        tb = max(f["total_blocks"], 1)
        pos_factor = 1.0 - (f["block_index"] / tb) * 0.05
        score *= pos_factor

        s = 1.0 / (1.0 + math.exp(-score))
        self._cache_score(key, s)
        return s

    # ---------------------------------------------------------
    # GPU scoring kernel (Numba) — optional
    # ---------------------------------------------------------
    def _gpu_score(self, f: Dict[str, Any]) -> float:
        from numba import cuda
        import numpy as np

        arr = np.array(
            [
                f["entropy_norm"],
                f["zero_ratio"],
                f["match4_norm"],
                f["delta4_score"],
                f["binary_strength"],
                f["ascii_ratio"],
                f["brace_ratio"],
                f["chunk_len"],
                f["kind_bonus"],
            ],
            dtype=np.float32,
        )

        w = np.array(
            [
                self.weights["entropy_norm"],
                self.weights["zero_ratio"],
                self.weights["match4_norm"],
                self.weights["delta4_score"],
                self.weights["binary_strength"],
                self.weights["ascii_ratio"],
                self.weights["brace_ratio"],
                self.weights["chunk_len"],
                self.weights["kind_bonus"],
            ],
            dtype=np.float32,
        )

        d_arr = cuda.to_device(arr)
        d_w = cuda.to_device(w)
        d_out = cuda.device_array(1, dtype=np.float32)

        @cuda.jit
        def dot_kernel(a, b, out):
            s = 0.0
            for i in range(a.size):
                s += a[i] * b[i]
            out[0] = s

        dot_kernel[1, 32](d_arr, d_w, d_out)
        score = float(d_out.copy_to_host()[0])

        return 1.0 / (1.0 + math.exp(-score))

    # ---------------------------------------------------------
    # Graph prediction
    # ---------------------------------------------------------
    def _predict_graph(self, s: float, f: Dict[str, Any]) -> Optional[str]:
        shape = f.get("shape", None)

        if shape == "JSON":
            return "JSON_GRAPH"
        if shape in ("TEXT", "UTF8"):
            return "TEXT_GRAPH"
        if shape == "BINARY":
            return "BINARY_GRAPH"
        if shape == "RANDOM":
            return "RANDOM_GRAPH"

        if s >= self.thresholds["high_structure"]:
            if f["brace_ratio"] > 0.02:
                return "JSON_GRAPH"
            if f["ascii_ratio"] > 0.6:
                return "TEXT_GRAPH"
            return "BINARY_GRAPH"

        if s >= self.thresholds["medium_structure"]:
            if f["ascii_ratio"] > 0.5:
                return "TEXT_GRAPH"
            return "BINARY_GRAPH"

        return "RANDOM_GRAPH"

    # ---------------------------------------------------------
    # Backend prediction (R/L/Z)
    # ---------------------------------------------------------
    def _predict_backend(self, s: float, f: Dict[str, Any]) -> Optional[str]:
        hint = f.get("backend_hint", None)
        if hint in ("R", "L", "Z"):
            return hint

        if s >= 0.75:
            if f["zero_ratio"] > 0.15:
                return "Z"
            return "L"

        if s >= 0.45:
            return "L"

        return "R"

    # ---------------------------------------------------------
    # Block size scaling
    # ---------------------------------------------------------
    def _predict_block_scale(self, s: float, f: Dict[str, Any]) -> float:
        if s >= 0.8:
            return 1.45
        if s >= 0.5:
            return 1.20
        return 0.85

    # ---------------------------------------------------------
    # BitDrop motif bias
    # ---------------------------------------------------------
    def _predict_bitdrop_bias(self, s: float, f: Dict[str, Any]) -> bool:
        if s >= self.thresholds["motif_prefer"]:
            if f["ascii_ratio"] > 0.6 or f["brace_ratio"] > 0.02:
                return True
        return False

    # ---------------------------------------------------------
    # Public prediction API (1D)
    # ---------------------------------------------------------
    def predict(self, features: Dict[str, Any]) -> PredictorOutput:
        """
        Main prediction entrypoint.

        Accepts partial feature dicts (older versions) and fills
        missing fields with safe defaults, so existing callers
        in BitDrop / compression / helper_mesh remain valid.
        """
        f: Dict[str, Any] = {
            "entropy": float(features.get("entropy", 6.0)),
            "entropy_norm": float(
                features.get("entropy_norm", features.get("entropy", 6.0) / 8.0)
            ),
            "zero_ratio": float(features.get("zero_ratio", 0.0)),
            "match4": float(features.get("match4", 0.0)),
            "match4_norm": float(
                features.get("match4_norm", features.get("match4", 0.0) / 10.0)
            ),
            "delta4_score": float(features.get("delta4_score", 0.0)),
            "binary_strength": float(features.get("binary_strength", 0.0)),
            "chunk_len": int(features.get("chunk_len", 0)),
            "ascii_ratio": float(features.get("ascii_ratio", 0.0)),
            "brace_ratio": float(features.get("brace_ratio", 0.0)),
            "kind_bonus": float(features.get("kind_bonus", 0.0)),
            "semantic_kind": features.get("semantic_kind", "unknown"),
            "shape": features.get("shape", None),
            "backend_hint": features.get("backend_hint", None),
            "block_index": int(features.get("block_index", 0)),
            "total_blocks": int(features.get("total_blocks", 1)),
            "file_size": int(features.get("file_size", 0)),
        }

        s = self._structure_score(f)
        graph = self._predict_graph(s, f)
        backend = self._predict_backend(s, f)
        block_scale = self._predict_block_scale(s, f)
        prefer_motif = self._predict_bitdrop_bias(s, f)

        return PredictorOutput(
            graph=graph,
            backend=backend,
            block_scale=block_scale,
            prefer_motif=prefer_motif,
            confidence=s,
        )

    # ---------------------------------------------------------
    # Batch prediction API (2D list)
    # ---------------------------------------------------------
    def predict_batch(self, features_list: List[Dict[str, Any]]) -> List[PredictorOutput]:
        return [self.predict(f) for f in features_list]

    # ---------------------------------------------------------
    # 3D tensor-style prediction API
    # ---------------------------------------------------------
    def predict_3d(
        self,
        features_3d: List[List[List[Dict[str, Any]]]],
    ) -> List[List[List[PredictorOutput]]]:
        depth = len(features_3d)
        if depth == 0:
            return []

        out: List[List[List[PredictorOutput]]] = []

        for d in range(depth):
            plane = features_3d[d]
            plane_out: List[List[PredictorOutput]] = []
            for row in plane:
                row_out: List[PredictorOutput] = []
                for f in row:
                    row_out.append(self.predict(f))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

