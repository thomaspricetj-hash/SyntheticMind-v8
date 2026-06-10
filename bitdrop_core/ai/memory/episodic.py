from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Episodic3D:
    """
    3D structural view of an episodic memory event.

    axis_x: raw event payload (stringified)
    axis_y: structural decomposition (keys, types)
    axis_z: metadata (timestamp, type, payload_size, index)
    """
    raw_payload: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


_last_3d: Optional[Episodic3D] = None


def _build_3d(entry: Dict[str, Any], index: int) -> Episodic3D:
    payload = entry.get("payload")
    payload_str = str(payload)

    # axis_y = structural decomposition of payload
    if isinstance(payload, dict):
        structure = [f"{k}:{type(v).__name__}" for k, v in payload.items()]
    elif isinstance(payload, list):
        structure = [type(v).__name__ for v in payload]
    else:
        structure = [type(payload).__name__]

    axis_z = {
        "timestamp": entry["ts"],
        "event_type": entry["type"],
        "payload_size": len(payload_str),
        "index": index,
    }

    return Episodic3D(
        raw_payload=payload_str,
        axis_x=payload_str,
        axis_y=structure,
        axis_z=axis_z,
    )


# ============================================================
# EPISODIC MEMORY (3D‑MAX)
# ============================================================

class EpisodicMemory:
    """
    Chronological event memory for SyntheticMind.
    Stores structured episodes with timestamps, type tags, and payloads.
    Now fully 3D‑MAX introspectable.
    """

    def __init__(self, max_events: int = 5000):
        self.max_events = max_events
        self.timeline: List[Dict[str, Any]] = []
        self._last_3d: Optional[Episodic3D] = None

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------

    def add(self, event_type: str, payload: Any):
        """
        Add a structured episodic event.
        event_type: "user_message", "assistant_reply", "action", etc.
        payload: arbitrary data (string, dict, etc.)
        """
        entry = {
            "ts": time.time(),
            "type": event_type,
            "payload": payload
        }

        self.timeline.append(entry)

        # Enforce capacity
        if len(self.timeline) > self.max_events:
            self.timeline.pop(0)

        # Build 3D structure
        index = len(self.timeline) - 1
        self._last_3d = _build_3d(entry, index)

        return entry

    def last(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return the last N events."""
        return self.timeline[-n:] if n > 0 else []

    def last_of_type(self, event_type: str, n: int = 5) -> List[Dict[str, Any]]:
        """Return the last N events of a given type."""
        filtered = [e for e in self.timeline if e["type"] == event_type]
        return filtered[-n:]

    def since(self, timestamp: float) -> List[Dict[str, Any]]:
        """Return all events after a given timestamp."""
        return [e for e in self.timeline if e["ts"] > timestamp]

    def dump(self) -> List[Dict[str, Any]]:
        """Return a full copy of the timeline (for debugging or export)."""
        return list(self.timeline)

    def clear(self):
        """Erase all episodic memory."""
        self.timeline.clear()
        self._last_3d = None

