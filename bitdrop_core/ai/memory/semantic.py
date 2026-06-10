from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time

from bitdrop_core.ai.compression.bitdrop_collapse_codec import BitDropCollapseEngine



# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Semantic3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# HYBRID SEMANTIC MEMORY — FACTS + BITDROP + 3D‑MAX
# ============================================================

class SemanticMemory:
    """
    Hybrid semantic memory.

    Stores:
        • key → collapsed value (BitDrop)
        • hybrid profile / version
        • 3D‑MAX telemetry

    Exposes:
        • set(key, value)  — auto‑collapse
        • get(key)         — auto‑expand
        • clear()
    """

    def __init__(self):
        self._facts: Dict[str, Dict[str, Any]] = {}
        self._bitdrop = BitDropCollapseEngine()
        self._last_3d: Optional[Semantic3D] = None

    # ------------------------------------------------------------
    # SET
    # ------------------------------------------------------------
    def set(self, key: str, value: str, profile: str = "balanced"):
        """
        Store a fact with hybrid collapse.
        """
        collapsed = self._bitdrop.collapse(value)
        collapsed_bytes = collapsed.encode("utf-8")

        self._facts[key] = {
            "collapsed": collapsed_bytes,
            "profile": profile,
            "version": 2,
            "created_at": time.time(),
        }

        self._last_3d = Semantic3D(
            axis_x="set",
            axis_y=[f"key:{key}", f"profile:{profile}"],
            axis_z={
                "len_raw": len(value),
                "len_collapsed": len(collapsed_bytes),
                "version": 2,
            },
        )

    # ------------------------------------------------------------
    # GET
    # ------------------------------------------------------------
    def get(self, key: str) -> Optional[str]:
        """
        Retrieve and expand a fact.
        """
        entry = self._facts.get(key)
        if not entry:
            self._last_3d = Semantic3D(
                axis_x="get",
                axis_y=[f"key:{key}"],
                axis_z={"found": False},
            )
            return None

        collapsed_bytes = entry["collapsed"]
        collapsed = collapsed_bytes.decode("utf-8")
        expanded = self._bitdrop.expand(collapsed)

        self._last_3d = Semantic3D(
            axis_x="get",
            axis_y=[f"key:{key}"],
            axis_z={
                "found": True,
                "profile": entry.get("profile", "balanced"),
                "version": entry.get("version", 2),
            },
        )

        return expanded

    # ------------------------------------------------------------
    # CLEAR
    # ------------------------------------------------------------
    def clear(self):
        self._facts.clear()
        self._last_3d = Semantic3D(
            axis_x="clear",
            axis_y=["facts:0"],
            axis_z={"status": "cleared"},
        )


