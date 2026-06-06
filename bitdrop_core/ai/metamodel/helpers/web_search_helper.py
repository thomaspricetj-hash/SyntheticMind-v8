import re
import zlib
from typing import Dict, Any, List, Optional

from ..context.packet import Packet


# ------------------------------------------------------------
# MICRO HELPERS
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()
    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.split())


class MicroTokenLimiter:
    __slots__ = ()
    @staticmethod
    def limit(text: str, max_chars: int = 5000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroSearchClassifier:
    __slots__ = ()
    STRONG = [
        "search the web", "search internet", "look up", "find info",
        "web search", "google", "bing", "ddg", "duckduckgo",
        "what is", "how much is", "price of", "cost of",
        "who is", "what are",
    ]

    @staticmethod
    def should_search(text: str) -> bool:
        t = text.lower()
        return any(k in t for k in MicroSearchClassifier.STRONG)


class MicroResultNormalizer:
    __slots__ = ()
    @staticmethod
    def normalize(raw: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        out = []
        for r in raw:
            out.append({
                "title": (r.get("title") or "").strip(),
                "snippet": (r.get("snippet") or "").strip(),
                "url": (r.get("url") or "").strip(),
            })
        return out


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class WebSearchHelper:
    """
    Ultra-fast WebSearchHelper with integrated micro-helpers.
    """

    def __init__(self, engine):
        self.engine = engine
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # Main entrypoint
    # ---------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Optional[Dict[str, Any]] = None,
        memory_info: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:

        query = (query or "").strip()
        if not query:
            return {"detected": False, "results": []}

        # Micro: normalize + limit
        query = MicroStringStripper.clean(query)
        query = MicroTokenLimiter.limit(query)

        # Micro: fast dedupe
        h = MicroFastHash.h(query)
        if h in self.cache:
            return self.cache[h]

        # Fast search-intent detection
        if not MicroSearchClassifier.should_search(query):
            return {"detected": False, "results": []}

        # Call the engine
        raw_results = self.engine.search(query, top_k=top_k) or []

        normalized = MicroResultNormalizer.normalize(raw_results)

        envelope = {
            "detected": True,
            "results": normalized,
        }

        # Cache
        self.cache[h] = envelope
        return envelope

