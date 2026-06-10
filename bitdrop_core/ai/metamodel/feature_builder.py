# bitdrop_core/ai/metamodel/feature_builder.py

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union


__all__ = ["BlockContext", "FeatureBuilder"]


BlockData = Union[bytes, str]


@dataclass
class BlockContext:
    """
    Lightweight context wrapper for a block.

    This is optional but makes it easy to pass around metadata
    without changing existing call sites too much.
    """
    data: BlockData
    block_index: int = 0
    total_blocks: int = 1
    file_size: int = 0
    semantic_kind: Optional[str] = None   # "json", "text", "binary", "unknown"
    backend_hint: Optional[str] = None    # "R", "L", "Z" or None
    shape_hint: Optional[str] = None      # "JSON", "TEXT", "BINARY", "RANDOM", etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeatureBuilder:
    """
    FeatureBuilder v8 — BitDrop + NeuralPredictor compatible.

    Responsibilities:
        - Accept raw blocks (bytes/str) + minimal context.
        - Compute structural + statistical features:
            • entropy
            • zero_ratio
            • ascii_ratio
            • brace_ratio
            • match4
            • delta4_score
            • binary_strength
            • chunk_len
        - Attach routing hints:
            • semantic_kind
            • backend_hint
            • shape
            • block_index / total_blocks / file_size
        - Return a dict directly consumable by NeuralPredictor.predict().
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}
        self._min_block_len: int = int(self.config.get("min_block_len", 1))

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def build_from_block(
        self,
        block: BlockData,
        block_index: int,
        total_blocks: int,
        file_size: int,
        semantic_kind: Optional[str] = None,
        backend_hint: Optional[str] = None,
        shape_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build a feature dict from a raw block and basic metadata.

        This is the main entrypoint you call from BitDrop / manager:

            features = feature_builder.build_from_block(
                block=data,
                block_index=i,
                total_blocks=n,
                file_size=total_size,
                semantic_kind=kind,
                backend_hint=hint,
                shape_hint=shape,
            )
        """

        ctx = BlockContext(
            data=block,
            block_index=block_index,
            total_blocks=max(total_blocks, 1),
            file_size=max(file_size, 0),
            semantic_kind=semantic_kind,
            backend_hint=backend_hint,
            shape_hint=shape_hint,
        )
        return self._build(ctx)

    def build_from_context(self, ctx: BlockContext) -> Dict[str, Any]:
        """
        Alternate entrypoint if you already wrap blocks in BlockContext.
        """
        return self._build(ctx)

    # ---------------------------------------------------------
    # Core builder
    # ---------------------------------------------------------
    def _build(self, ctx: BlockContext) -> Dict[str, Any]:
        data = ctx.data
        if isinstance(data, str):
            raw_bytes = data.encode("utf-8", errors="ignore")
            text = data
        else:
            raw_bytes = data
            text = self._safe_decode(raw_bytes)

        chunk_len = max(len(raw_bytes), self._min_block_len)

        entropy = self._entropy(raw_bytes)
        zero_ratio = self._zero_ratio(raw_bytes)
        ascii_ratio = self._ascii_ratio(raw_bytes)
        brace_ratio = self._brace_ratio(text)
        match4 = self._match4_score(raw_bytes)
        delta4_score = self._delta4_score(raw_bytes)
        binary_strength = self._binary_strength(raw_bytes, ascii_ratio)

        semantic_kind = ctx.semantic_kind or self._infer_semantic_kind(
            ascii_ratio=ascii_ratio,
            brace_ratio=brace_ratio,
        )
        shape = ctx.shape_hint or self._infer_shape(
            semantic_kind=semantic_kind,
            ascii_ratio=ascii_ratio,
            brace_ratio=brace_ratio,
        )

        features: Dict[str, Any] = {
            "entropy": float(entropy),
            "zero_ratio": float(zero_ratio),
            "match4": float(match4),
            "delta4_score": float(delta4_score),
            "binary_strength": float(binary_strength),
            "chunk_len": int(chunk_len),
            "ascii_ratio": float(ascii_ratio),
            "brace_ratio": float(brace_ratio),
            "semantic_kind": semantic_kind,
            "shape": shape,
            "backend_hint": ctx.backend_hint,
            "block_index": int(ctx.block_index),
            "total_blocks": int(ctx.total_blocks),
            "file_size": int(ctx.file_size),
        }

        # NeuralPredictor will derive entropy_norm / match4_norm / kind_bonus,
        # but we can precompute them if you want tighter control.
        features["entropy_norm"] = float(entropy / 8.0)
        features["match4_norm"] = float(match4 / 10.0)
        features["kind_bonus"] = float(self._kind_bonus(semantic_kind))

        return features
# bitdrop_core/ai/metamodel/feature_builder.py



import math
import zlib
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Union, List


__all__ = ["BlockContext", "FeatureBuilder", "FeatureBuilder3D"]


BlockData = Union[bytes, str]


# ---------------------------------------------------------
# MICRO HELPERS
# ---------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()

    @staticmethod
    def clean_text(text: str) -> str:
        return " ".join((text or "").split())


class MicroFastHash:
    __slots__ = ()

    @staticmethod
    def h_bytes(data: bytes) -> int:
        return zlib.crc32(data)

    @staticmethod
    def h_text(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


@dataclass
class BlockContext:
    """
    Lightweight context wrapper for a block.

    This is optional but makes it easy to pass around metadata
    without changing existing call sites too much.
    """
    data: BlockData
    block_index: int = 0
    total_blocks: int = 1
    file_size: int = 0
    semantic_kind: Optional[str] = None   # "json", "text", "binary", "unknown"
    backend_hint: Optional[str] = None    # "R", "L", "Z" or None
    shape_hint: Optional[str] = None      # "JSON", "TEXT", "BINARY", "RANDOM", etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FeatureBuilder:
    """
    FeatureBuilder v8 — BitDrop + NeuralPredictor compatible.

    Responsibilities:
        - Accept raw blocks (bytes/str) + minimal context.
        - Compute structural + statistical features:
            • entropy
            • zero_ratio
            • ascii_ratio
            • brace_ratio
            • match4
            • delta4_score
            • binary_strength
            • chunk_len
        - Attach routing hints:
            • semantic_kind
            • backend_hint
            • shape
            • block_index / total_blocks / file_size
        - Return a dict directly consumable by NeuralPredictor.predict().
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}
        self._min_block_len: int = int(self.config.get("min_block_len", 1))
        self._feature_cache: Dict[int, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def build_from_block(
        self,
        block: BlockData,
        block_index: int,
        total_blocks: int,
        file_size: int,
        semantic_kind: Optional[str] = None,
        backend_hint: Optional[str] = None,
        shape_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        ctx = BlockContext(
            data=block,
            block_index=block_index,
            total_blocks=max(total_blocks, 1),
            file_size=max(file_size, 0),
            semantic_kind=semantic_kind,
            backend_hint=backend_hint,
            shape_hint=shape_hint,
        )
        return self._build(ctx)

    def build_from_context(self, ctx: BlockContext) -> Dict[str, Any]:
        return self._build(ctx)

    # ---------------------------------------------------------
    # Core builder (cached)
    # ---------------------------------------------------------
    def _build(self, ctx: BlockContext) -> Dict[str, Any]:
        data = ctx.data
        if isinstance(data, str):
            text = MicroStringStripper.clean_text(data)
            raw_bytes = text.encode("utf-8", errors="ignore")
            key_hash = MicroFastHash.h_text(text)
        else:
            raw_bytes = data
            text = self._safe_decode(raw_bytes)
            key_hash = MicroFastHash.h_bytes(raw_bytes)

        cached = self._feature_cache.get(key_hash)
        if cached is not None:
            # still override contextual fields that can change per block
            out = dict(cached)
            out["backend_hint"] = ctx.backend_hint
            out["block_index"] = int(ctx.block_index)
            out["total_blocks"] = int(ctx.total_blocks)
            out["file_size"] = int(ctx.file_size)
            return out

        chunk_len = max(len(raw_bytes), self._min_block_len)

        entropy = self._entropy(raw_bytes)
        zero_ratio = self._zero_ratio(raw_bytes)
        ascii_ratio = self._ascii_ratio(raw_bytes)
        brace_ratio = self._brace_ratio(text)
        match4 = self._match4_score(raw_bytes)
        delta4_score = self._delta4_score(raw_bytes)
        binary_strength = self._binary_strength(raw_bytes, ascii_ratio)

        semantic_kind = ctx.semantic_kind or self._infer_semantic_kind(
            ascii_ratio=ascii_ratio,
            brace_ratio=brace_ratio,
        )
        shape = ctx.shape_hint or self._infer_shape(
            semantic_kind=semantic_kind,
            ascii_ratio=ascii_ratio,
            brace_ratio=brace_ratio,
        )

        features: Dict[str, Any] = {
            "entropy": float(entropy),
            "zero_ratio": float(zero_ratio),
            "match4": float(match4),
            "delta4_score": float(delta4_score),
            "binary_strength": float(binary_strength),
            "chunk_len": int(chunk_len),
            "ascii_ratio": float(ascii_ratio),
            "brace_ratio": float(brace_ratio),
            "semantic_kind": semantic_kind,
            "shape": shape,
            "backend_hint": ctx.backend_hint,
            "block_index": int(ctx.block_index),
            "total_blocks": int(ctx.total_blocks),
            "file_size": int(ctx.file_size),
        }

        features["entropy_norm"] = float(entropy / 8.0)
        features["match4_norm"] = float(match4 / 10.0)
        features["kind_bonus"] = float(self._kind_bonus(semantic_kind))

        # cache base structural features (context-free)
        base_cache = dict(features)
        base_cache["backend_hint"] = None
        base_cache["block_index"] = 0
        base_cache["total_blocks"] = 1
        base_cache["file_size"] = 0
        self._feature_cache[key_hash] = base_cache

        return features

    # ---------------------------------------------------------
    # Low-level metrics
    # ---------------------------------------------------------
    def _safe_decode(self, data: bytes) -> str:
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        counts: Dict[int, int] = {}
        for b in data:
            counts[b] = counts.get(b, 0) + 1
        length = float(len(data))
        entropy = 0.0
        for c in counts.values():
            p = c / length
            entropy -= p * math.log2(p)
        return entropy

    def _zero_ratio(self, data: bytes) -> float:
        if not data:
            return 0.0
        zeros = sum(1 for b in data if b == 0)
        return zeros / float(len(data))

    def _ascii_ratio(self, data: bytes) -> float:
        if not data:
            return 0.0
        ascii_count = sum(1 for b in data if 32 <= b <= 126 or b in (9, 10, 13))
        return ascii_count / float(len(data))

    def _brace_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        braces = "{}[]"
        brace_count = sum(1 for ch in text if ch in braces)
        return brace_count / float(len(text))

    def _match4_score(self, data: bytes) -> float:
        n = len(data)
        if n < 8:
            return 0.0

        window_counts: Dict[bytes, int] = {}
        limit = n - 3
        for i in range(limit):
            w = data[i : i + 4]
            window_counts[w] = window_counts.get(w, 0) + 1

        repeats = sum(1 for c in window_counts.values() if c > 1)
        total_windows = float(max(len(window_counts), 1))
        return repeats / total_windows

    def _delta4_score(self, data: bytes) -> float:
        n = len(data)
        if n < 8:
            return 0.0

        deltas = []
        limit = n - 4
        for i in range(limit):
            d = int(data[i + 4]) - int(data[i])
            deltas.append(d)

        if not deltas:
            return 0.0

        mean = sum(deltas) / float(len(deltas))
        var = sum((d - mean) * (d - mean) for d in deltas) / float(len(deltas))
        return 1.0 / (1.0 + var / 256.0)

    def _binary_strength(self, data: bytes, ascii_ratio: float) -> float:
        if not data:
            return 0.0
        non_ascii = 1.0 - ascii_ratio
        zero_r = self._zero_ratio(data)
        return min(1.0, non_ascii * 0.7 + zero_r * 0.3)

    # ---------------------------------------------------------
    # Semantic + shape inference
    # ---------------------------------------------------------
    def _infer_semantic_kind(self, ascii_ratio: float, brace_ratio: float) -> str:
        if ascii_ratio > 0.95 and brace_ratio > 0.01:
            return "json"
        if ascii_ratio > 0.85:
            return "text"
        if ascii_ratio < 0.3:
            return "binary"
        return "unknown"

    def _infer_shape(self, semantic_kind: str, ascii_ratio: float, brace_ratio: float) -> Optional[str]:
        if semantic_kind == "json":
            return "JSON"
        if semantic_kind == "text":
            return "TEXT"
        if semantic_kind == "binary":
            return "BINARY"

        if brace_ratio > 0.02 and ascii_ratio > 0.6:
            return "JSON"
        if ascii_ratio > 0.6:
            return "TEXT"
        if ascii_ratio < 0.3:
            return "BINARY"

        return "RANDOM"

    def _kind_bonus(self, semantic_kind: str) -> float:
        if semantic_kind == "json":
            return 0.45
        if semantic_kind == "text":
            return 0.30
        if semantic_kind == "binary":
            return 0.15
        return 0.0


# ---------------------------------------------------------
# 3D MAX WRAPPER
# ---------------------------------------------------------
class FeatureBuilder3D:
    """
    3D-max FeatureBuilder:
        • Reuses FeatureBuilder core logic
        • Accepts 3D grids [D][H][W] of blocks/contexts
        • Returns 3D grids of feature dicts
        • Amplifies cache across the 3D mesh
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.builder = FeatureBuilder(config=config)

    def build_from_block_3d(
        self,
        blocks_3d: List[List[List[BlockData]]],
        block_indices_3d: List[List[List[int]]],
        total_blocks_3d: List[List[List[int]]],
        file_sizes_3d: List[List[List[int]]],
        semantic_kinds_3d: Optional[List[List[List[Optional[str]]]]] = None,
        backend_hints_3d: Optional[List[List[List[Optional[str]]]]] = None,
        shape_hints_3d: Optional[List[List[List[Optional[str]]]]] = None,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(blocks_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane_b = blocks_3d[d]
            plane_i = block_indices_3d[d]
            plane_t = total_blocks_3d[d]
            plane_f = file_sizes_3d[d]
            plane_s = semantic_kinds_3d[d] if semantic_kinds_3d is not None else None
            plane_back = backend_hints_3d[d] if backend_hints_3d is not None else None
            plane_shape = shape_hints_3d[d] if shape_hints_3d is not None else None

            plane_out: List[List[Dict[str, Any]]] = []
            for r_idx, row_b in enumerate(plane_b):
                row_i = plane_i[r_idx]
                row_t = plane_t[r_idx]
                row_f = plane_f[r_idx]
                row_s = plane_s[r_idx] if plane_s is not None else None
                row_back = plane_back[r_idx] if plane_back is not None else None
                row_shape = plane_shape[r_idx] if plane_shape is not None else None

                row_out: List[Dict[str, Any]] = []
                for c_idx, block in enumerate(row_b):
                    features = self.builder.build_from_block(
                        block=block,
                        block_index=row_i[c_idx],
                        total_blocks=row_t[c_idx],
                        file_size=row_f[c_idx],
                        semantic_kind=row_s[c_idx] if row_s is not None else None,
                        backend_hint=row_back[c_idx] if row_back is not None else None,
                        shape_hint=row_shape[c_idx] if row_shape is not None else None,
                    )
                    row_out.append(features)
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def build_from_context_3d(
        self,
        contexts_3d: List[List[List[BlockContext]]],
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(contexts_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = contexts_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for ctx in row:
                    row_out.append(self.builder.build_from_context(ctx))
                plane_out.append(row_out)
            out.append(plane_out)

        return out
