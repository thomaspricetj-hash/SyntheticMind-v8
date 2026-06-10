from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import re
import zlib

from ..context.packet import Packet


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class WebSearch3D:
    """
    3D structural view of web-search analysis.

    axis_x: raw query
    axis_y: token/line decomposition
    axis_z: search metadata + results
    """
    raw_query: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


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
# MAIN HELPER (3D-AWARE)
# ------------------------------------------------------------
class WebSearchHelper:
    """
    Ultra-fast WebSearchHelper with integrated micro-helpers + 3D structural output.
    """

    def __init__(self, engine):
        self.engine = engine
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ---------------------------------------------------------
    # 3D builder
    # ---------------------------------------------------------
    def _build_3d(self, query: str, detected: bool, results: List[Dict[str, str]]) -> WebSearch3D:
        lines = (query or "").splitlines()
        axis_z = {
            "detected": detected,
            "result_count": len(results),
            "results": results,
            "tokens": re.findall(r"\S+", query or ""),
        }
        return WebSearch3D(
            raw_query=query or "",
            axis_x=query or "",
            axis_y=lines,
            axis_z=axis_z,
        )

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
            structure_3d = self._build_3d("", False, [])
            return {"detected": False, "results": [], "structure_3d": structure_3d}

        # Micro: normalize + limit
        query = MicroStringStripper.clean(query)
        query = MicroTokenLimiter.limit(query)

        # Micro: fast dedupe
        h = MicroFastHash.h(query)
        if h in self.cache:
            cached = self.cache[h]
            cached["structure_3d"] = self._build_3d(query, cached["detected"], cached["results"])
            return cached

        # Fast search-intent detection
        if not MicroSearchClassifier.should_search(query):
            structure_3d = self._build_3d(query, False, [])
            return {"detected": False, "results": [], "structure_3d": structure_3d}

        # Call the engine
        raw_results = self.engine.search(query, top_k=top_k) or []
        normalized = MicroResultNormalizer.normalize(raw_results)

        envelope = {
            "detected": True,
            "results": normalized,
        }

        # Cache
        self.cache[h] = envelope

        # Attach 3D structure
        envelope["structure_3d"] = self._build_3d(query, True, normalized)

        return envelope


