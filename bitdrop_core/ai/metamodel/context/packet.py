from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import hashlib
import time


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Packet3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# PACKET — MAX CONTAINER + 3D‑MAX
# ============================================================

@dataclass
class Packet:
    """
    Universal message container for the BitDrop MetaModel system (3D‑MAX Edition).

    Features:
        • text or binary payload
        • routing metadata
        • compression metadata
        • integrity fingerprint v2
        • multimodal safety
        • safe copying
        • structured serialization
        • 3D‑MAX telemetry
    """

    # ------------------------------------------------------------
    # CORE CONTENT
    # ------------------------------------------------------------
    text: str = ""                     # User text or prompt
    query: Optional[str] = None        # Raw user query (un-augmented)
    data: Optional[bytes] = None       # Optional binary payload

    # General metadata (user, session, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Benchmark metadata (kept separate)
    benchmark_metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------
    # ROUTING METADATA
    # ------------------------------------------------------------
    intent: str = "small_reasoning"
    model: Optional[str] = None
    compressed: bool = False
    return_compressed: bool = False

    # ------------------------------------------------------------
    # SYSTEM METADATA
    # ------------------------------------------------------------
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    # ------------------------------------------------------------
    # INTERNAL — LAST 3D‑MAX SNAPSHOT
    # ------------------------------------------------------------
    _last_3d: Optional[Packet3D] = None

    # ------------------------------------------------------------
    # FINGERPRINT V2
    # ------------------------------------------------------------
    def fingerprint(self) -> str:
        """
        Compute a stable fingerprint of the packet contents.
        Includes:
            • text
            • binary payload
            • routing metadata
            • metadata + benchmark metadata
        """

        h = hashlib.sha256()

        h.update(self.text.encode("utf-8"))

        if self.data:
            h.update(self.data)

        # Routing metadata
        h.update((self.intent or "").encode("utf-8"))
        h.update((self.model or "").encode("utf-8"))

        # Metadata (stable ordering)
        for k in sorted(self.metadata.keys()):
            h.update(f"{k}:{self.metadata[k]}".encode("utf-8"))

        for k in sorted(self.benchmark_metadata.keys()):
            h.update(f"bench:{k}:{self.benchmark_metadata[k]}".encode("utf-8"))

        return h.hexdigest()

    # ------------------------------------------------------------
    # SAFE COPY
    # ------------------------------------------------------------
    def copy(self, **updates) -> "Packet":
        """
        Create a modified copy of this Packet.
        Ensures immutability of original packet.
        Deep-copies metadata dictionaries.
        """

        fields = {
            "text": self.text,
            "query": self.query,
            "data": self.data,
            "metadata": dict(self.metadata),
            "benchmark_metadata": dict(self.benchmark_metadata),
            "intent": self.intent,
            "model": self.model,
            "compressed": self.compressed,
            "return_compressed": self.return_compressed,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }

        fields.update(updates)

        new_packet = Packet(**fields)

        # 3D‑MAX telemetry
        new_packet._last_3d = Packet3D(
            axis_x="copy",
            axis_y=list(updates.keys()),
            axis_z={"ok": True},
        )

        return new_packet

    # ------------------------------------------------------------
    # STRUCTURED SERIALIZATION
    # ------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a structured, serializable dictionary.
        Safe for logging, debugging, and external inspection.
        """

        # 3D‑MAX telemetry snapshot
        self._last_3d = Packet3D(
            axis_x="to_dict",
            axis_y=[
                f"text_len:{len(self.text)}",
                f"binary:{self.data is not None}",
            ],
            axis_z={
                "compressed": self.compressed,
                "intent": self.intent,
                "model": self.model,
            },
        )

        return {
            "text": self.text,
            "query": self.query,
            "metadata": self.metadata,
            "benchmark_metadata": self.benchmark_metadata,
            "intent": self.intent,
            "model": self.model,
            "compressed": self.compressed,
            "return_compressed": self.return_compressed,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "has_binary": self.data is not None,
            "binary_size": len(self.data) if self.data else 0,
            "fingerprint": self.fingerprint(),
        }



