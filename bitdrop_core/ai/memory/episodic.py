import time
from typing import List, Dict, Any, Optional


class EpisodicMemory:
    """
    Chronological event memory for SyntheticMind.
    Stores structured episodes with timestamps, type tags, and payloads.
    """

    def __init__(self, max_events: int = 5000):
        self.max_events = max_events
        self.timeline: List[Dict[str, Any]] = []

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
