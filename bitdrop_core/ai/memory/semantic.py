# ai/memory/semantic.py

from __future__ import annotations
from typing import Dict, Any, Optional, List


class SemanticMemory:
    """
    Stores stable, structured facts and knowledge.
    Supports:
      • key-value storage
      • namespaces (categories)
      • fuzzy lookup
      • prefix search
      • safe overwrite rules
    """

    def __init__(self):
        # facts are stored as: { "key": {"value": ..., "meta": {...}} }
        self.facts: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # CORE OPERATIONS
    # ------------------------------------------------------------

    def set(self, key: str, value: Any, *, overwrite: bool = True, meta: Optional[dict] = None):
        """
        Store a semantic fact.
        overwrite=False prevents accidental replacement.
        meta can include: source, confidence, timestamp, tags, etc.
        """
        if not key:
            return False

        if key in self.facts and not overwrite:
            return False

        self.facts[key] = {
            "value": value,
            "meta": meta or {}
        }
        return True

    def get(self, key: str) -> Optional[Any]:
        """Retrieve the value of a fact."""
        entry = self.facts.get(key)
        return entry["value"] if entry else None

    def delete(self, key: str) -> bool:
        """Remove a fact."""
        return self.facts.pop(key, None) is not None

    # ------------------------------------------------------------
    # SEARCH / QUERY
    # ------------------------------------------------------------

    def keys(self) -> List[str]:
        """Return all fact keys."""
        return list(self.facts.keys())

    def all(self) -> Dict[str, Dict[str, Any]]:
        """Return full structured fact store."""
        return dict(self.facts)

    def search_prefix(self, prefix: str) -> Dict[str, Any]:
        """Return all facts whose keys start with the given prefix."""
        return {
            k: v["value"]
            for k, v in self.facts.items()
            if k.startswith(prefix)
        }

    def search_contains(self, substring: str) -> Dict[str, Any]:
        """Return all facts whose keys contain the substring."""
        return {
            k: v["value"]
            for k, v in self.facts.items()
            if substring in k
        }

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------

    def export(self) -> Dict[str, Dict[str, Any]]:
        """Return a deep copy for persistence."""
        return {k: dict(v) for k, v in self.facts.items()}

    def import_from(self, data: Dict[str, Dict[str, Any]]):
        """Load facts from a saved dictionary."""
        for k, v in data.items():
            if isinstance(v, dict) and "value" in v:
                self.facts[k] = v

    def clear(self):
        """Erase all semantic memory."""
        self.facts.clear()

