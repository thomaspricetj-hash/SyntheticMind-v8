from __future__ import annotations
from typing import Any, Dict, List
import unicodedata
import re
import zlib


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
    def limit(text: str, max_chars: int = 8000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroRegex:
    __slots__ = ()
    SYMBOLS = re.compile(r"[^\w\s]")
    SENTENCES = re.compile(r"[.!?]+")
    ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\uFEFF]")


class MicroQueryClassifier:
    __slots__ = ()
    @staticmethod
    def classify(text: str) -> str:
        t = text.lower()

        # Fast-path checks
        if any(h in t for h in ("solve", "equation", "integral", "derivative", "=")):
            return "math"
        if any(h in t for h in ("def ", "class ", "import ", "=>", "console.log")):
            return "code"
        if any(h in t for h in ("prove", "implies", "contradiction", "therefore")):
            return "logic"
        if any(h in t for h in ("quantum", "force", "energy", "relativity", "field")):
            return "physics"

        return "natural_language"


class MicroParagraphNormalizer:
    __slots__ = ()
    @staticmethod
    def normalize(text: str) -> str:
        parts = text.split("\n")
        cleaned = []
        for p in parts:
            p = p.strip()
            if p:
                cleaned.append(" ".join(p.split()))
        return "\n".join(cleaned)


# ------------------------------------------------------------
# MAIN HELPER (1D)
# ------------------------------------------------------------
class LanguageHelper:
    """
    Ultra-fast LanguageHelper with integrated micro-helpers.
    """

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}

    def _classify_query(self, text: str) -> str:
        return MicroQueryClassifier.classify(text)

    def _normalize(self, text: str) -> str:
        cleaned = unicodedata.normalize("NFC", text)
        cleaned = MicroRegex.ZERO_WIDTH.sub("", cleaned)
        cleaned = MicroParagraphNormalizer.normalize(cleaned)
        cleaned = re.sub(r"([!?.,])\1{1,}", r"\1", cleaned)
        return cleaned

    def _extract_structure(self, text: str) -> Dict[str, Any]:
        tokens = text.split()
        sentences = [s.strip() for s in MicroRegex.SENTENCES.split(text) if s.strip()]
        symbols = MicroRegex.SYMBOLS.findall(text)

        return {
            "tokens": len(tokens),
            "sentences": len(sentences),
            "symbols": symbols,
            "paragraphs": text.count("\n") + 1,
        }

    def process(self, query: str) -> Dict[str, Any]:
        try:
            query = (query or "").strip()
            if not query:
                return {
                    "clarified_query": "",
                    "length": 0,
                    "query_type": "empty",
                    "structure": {},
                }

            query = MicroStringStripper.clean(query)
            query = MicroTokenLimiter.limit(query)

            h = MicroFastHash.h(query)
            cached = self.cache.get(h)
            if cached is not None:
                return cached

            cleaned = self._normalize(query)
            qtype = self._classify_query(cleaned)
            structure = self._extract_structure(cleaned)

            envelope = {
                "clarified_query": cleaned,
                "length": structure["tokens"],
                "query_type": qtype,
                "structure": structure,
            }

            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "clarified_query": query,
                "length": len(query.split()),
                "query_type": "error",
                "structure": {},
                "error": str(e),
            }


# ------------------------------------------------------------
# 3D LANGUAGE HELPER (MAXED, BACKWARD-COMPATIBLE)
# ------------------------------------------------------------
class LanguageHelper3D:
    """
    3D LanguageHelper:
        • Reuses LanguageHelper core logic
        • Adds 3D grids of queries: [D][H][W]
        • Per-cell normalization + classification
        • Deterministic 3D envelopes
        • Cache amplification across 3D space
    """

    def __init__(self) -> None:
        self.helper = LanguageHelper()

    def process_3d(
        self,
        queries_3d: List[List[List[str]]],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        queries_3d[d][h][w] = query string
        returns envelopes_3d[d][h][w] = LanguageHelper envelope
        """
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(self.helper.process(q))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def classify_3d(
        self,
        queries_3d: List[List[List[str]]],
    ) -> List[List[List[str]]]:
        """
        Convenience: return only query_type per cell.
        """
        envelopes_3d = self.process_3d(queries_3d)
        depth = len(envelopes_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = envelopes_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for env in row:
                    row_out.append(env.get("query_type", "unknown"))
                plane_out.append(row_out)
            out.append(plane_out)

        return out
