from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class MemoryItem3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# MEMORY ITEM — STRICT M2 + HYBRID + 3D‑MAX
# ============================================================

@dataclass
class MemoryItem:
    """
    Strict‑M2 memory item with hybrid BitDrop support.

    Fields:
        • embedding: vector representation
        • bloom: token hash set
        • patterns: signature dict
        • bitdrop_binary: bytes (required)
        • hybrid_profile: fast | balanced | max
        • bitdrop_version: 2 or 3
        • collapse_rules: optional rule dict
        • collapse_tags: optional tag dict
        • created_at: timestamp
        • last_access: timestamp
        • access_count: int
        • 3D‑MAX telemetry
    """

    embedding: List[float]
    bloom: set
    patterns: Dict[str, Any]
    bitdrop_binary: bytes

    # HYBRID METADATA
    hybrid_profile: str = "balanced"
    bitdrop_version: int = 2
    collapse_rules: Optional[Dict[str, Any]] = field(default_factory=dict)
    collapse_tags: Optional[Dict[str, Any]] = field(default_factory=dict)

    # RUNTIME METADATA
    created_at: float = field(default_factory=lambda: time.time())
    last_access: float = field(default_factory=lambda: time.time())
    access_count: int = 0

    # 3D‑MAX telemetry
    _last_3d: Optional[MemoryItem3D] = None

    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------
    def __post_init__(self):
        # embedding must be list of floats
        if not isinstance(self.embedding, list):
            raise TypeError("embedding must be a list of floats")

        # bloom must be a set
        if not isinstance(self.bloom, set):
            raise TypeError("bloom must be a set")

        # patterns must be a dict
        if not isinstance(self.patterns, dict):
            raise TypeError("patterns must be a dict")

        # bitdrop_binary must be bytes
        if not isinstance(self.bitdrop_binary, (bytes, bytearray)):
            raise TypeError("bitdrop_binary must be bytes")

        # hybrid profile sanity
        if self.hybrid_profile not in ("fast", "balanced", "max"):
            self.hybrid_profile = "balanced"

        # bitdrop version sanity
        if self.bitdrop_version not in (2, 3):
            self.bitdrop_version = 2

        # 3D‑MAX telemetry
        self._last_3d = MemoryItem3D(
            axis_x="init",
            axis_y=[f"embedding_dim:{len(self.embedding)}"],
            axis_z={
                "bloom_size": len(self.bloom),
                "patterns": list(self.patterns.keys()),
                "bitdrop_bytes": len(self.bitdrop_binary),
                "profile": self.hybrid_profile,
                "version": self.bitdrop_version,
            },
        )

    # ------------------------------------------------------------
    # ACCESS TRACKING
    # ------------------------------------------------------------
    def touch(self):
        """
        Update last_access + access_count.
        """
        self.last_access = time.time()
        self.access_count += 1

        self._last_3d = MemoryItem3D(
            axis_x="touch",
            axis_y=[f"access_count:{self.access_count}"],
            axis_z={"last_access": self.last_access},
        )

    # ------------------------------------------------------------
    # EXPORT (for MemoryStore)
    # ------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON‑serializable dict for MemoryStore.
        """
        return {
            "embedding": self.embedding,
            "bloom": list(self.bloom),
            "patterns": self.patterns,
            "bitdrop_binary": list(self.bitdrop_binary),  # bytes → list[int]
            "hybrid_profile": self.hybrid_profile,
            "bitdrop_version": self.bitdrop_version,
            "collapse_rules": self.collapse_rules,
            "collapse_tags": self.collapse_tags,
            "created_at": self.created_at,
            "last_access": self.last_access,
            "access_count": self.access_count,
        }

    # ------------------------------------------------------------
    # IMPORT (from MemoryStore)
    # ------------------------------------------------------------
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MemoryItem":
        """
        Reconstruct MemoryItem from MemoryStore payload.
        """
        return MemoryItem(
            embedding=data.get("embedding", []),
            bloom=set(data.get("bloom", [])),
            patterns=data.get("patterns", {}),
            bitdrop_binary=bytes(data.get("bitdrop_binary", [])),
            hybrid_profile=data.get("hybrid_profile", "balanced"),
            bitdrop_version=data.get("bitdrop_version", 2),
            collapse_rules=data.get("collapse_rules", {}),
            collapse_tags=data.get("collapse_tags", {}),
            created_at=data.get("created_at", time.time()),
            last_access=data.get("last_access", time.time()),
            access_count=data.get("access_count", 0),
        )
