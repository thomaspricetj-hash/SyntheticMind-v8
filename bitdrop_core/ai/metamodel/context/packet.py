from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import hashlib
import time


@dataclass
class Packet:
    """
    Universal message container for the BitDrop MetaModel system.
    Every request entering the router is wrapped in a Packet.

    Features:
        • text or binary payload
        • routing metadata
        • compression metadata
        • integrity fingerprint
        • safe copying
        • structured serialization
    """

    # ------------------------------------------------------------
    # CORE CONTENT
    # ------------------------------------------------------------
    text: str = ""                     # User text or prompt

    # ⭐ ADDED FIELD — REQUIRED FOR SELF‑AUDIT + INTROSPECTION
    query: Optional[str] = None        # Raw user query (un-augmented)

    data: Optional[bytes] = None       # Optional binary payload
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------
    # ROUTING METADATA
    # ------------------------------------------------------------
    intent: str = "small_reasoning"    # small_reasoning, large_reasoning, code, math, vision, etc.
    model: Optional[str] = None        # override model selection
    compressed: bool = False           # input is compressed
    return_compressed: bool = False    # output should be compressed

    # ------------------------------------------------------------
    # SYSTEM METADATA
    # ------------------------------------------------------------
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    # ------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------
    def fingerprint(self) -> str:
        """
        Compute a stable fingerprint of the packet contents.
        Used for debugging, caching, and integrity checks.
        """

        h = hashlib.sha256()

        h.update(self.text.encode("utf-8"))
        if self.data:
            h.update(self.data)

        # Include routing metadata
        h.update((self.intent or "").encode("utf-8"))
        h.update((self.model or "").encode("utf-8"))

        return h.hexdigest()

    # ------------------------------------------------------------
    def copy(self, **updates) -> "Packet":
        """
        Create a modified copy of this Packet.
        Ensures immutability of original packet.
        """

        fields = {
            "text": self.text,
            "query": self.query,   # ⭐ ensure copy preserves query
            "data": self.data,
            "metadata": dict(self.metadata),
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
        return Packet(**fields)

    # ------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to a structured, serializable dictionary.
        Safe for logging, debugging, and external inspection.
        """

        return {
            "text": self.text,
            "query": self.query,   # ⭐ include query in logs
            "metadata": self.metadata,
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


