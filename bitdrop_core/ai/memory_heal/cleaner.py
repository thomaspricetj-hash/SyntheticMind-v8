# ai/memory/memory_cleaner.py

from __future__ import annotations
from typing import Dict, Any, List


class MemoryCleaner:
    """
    Applies healing operations to memory:
        • deduplication
        • contradiction flagging
        • noise removal
        • quarantine of suspicious items
        • structured cleanup reporting
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    # ------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------
    def clean(self, issues: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform a cleanup cycle.
        Returns a structured report describing what was changed.
        """

        removed = []
        flagged = []
        quarantined = []

        # --------------------------------------------------------
        # 1. Remove duplicates
        # --------------------------------------------------------
        for item in issues.get("duplicates", []):
            if self._safe_remove(item):
                removed.append(item)

        # --------------------------------------------------------
        # 2. Flag contradictions
        # --------------------------------------------------------
        for c in issues.get("contradictions", []):
            self.runtime.memory.remember(f"[flagged-contradiction] {c}")
            flagged.append(c)

        # --------------------------------------------------------
        # 3. Remove noise
        # --------------------------------------------------------
        for n in issues.get("noise", []):
            if self._safe_remove(n):
                removed.append(n)

        # --------------------------------------------------------
        # 4. Quarantine suspicious items
        # --------------------------------------------------------
        for q in issues.get("suspicious", []):
            self.runtime.memory.remember(f"[quarantine] {q}")
            quarantined.append(q)

        # --------------------------------------------------------
        # 5. Structured cleanup report
        # --------------------------------------------------------
        return {
            "removed": removed,
            "flagged": flagged,
            "quarantined": quarantined,
            "total_actions": len(removed) + len(flagged) + len(quarantined),
        }

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _safe_remove(self, item: Any) -> bool:
        """
        Remove an item only if:
            • it exists
            • it is not a high‑value fact
            • it is not a skill
            • it is not a preference
        """

        text = str(item).lower()

        # Protect high‑value memory
        protected_prefixes = (
            "[fact]",
            "[skill]",
            "[preference]",
            "[theme]",
            "[trend]",
        )

        if any(text.startswith(p) for p in protected_prefixes):
            # Do not remove high‑value items
            return False

        try:
            self.runtime.memory.remove(item)
            return True
        except Exception:
            return False
