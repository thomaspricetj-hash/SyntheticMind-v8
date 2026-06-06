from __future__ import annotations
from typing import Any, Dict
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
        # Preserve paragraph boundaries but normalize inside each
        parts = text.split("\n")
        cleaned = []
        for p in parts:
            p = p.strip()
            if p:
                cleaned.append(" ".join(p.split()))
        return "\n".join(cleaned)


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class LanguageHelper:
    """
    Ultra-fast LanguageHelper with integrated micro-helpers.
    """

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: classify query type
    # ------------------------------------------------------------
    def _classify_query(self, text: str) -> str:
        return MicroQueryClassifier.classify(text)

    # ------------------------------------------------------------
    # INTERNAL: normalize text
    # ------------------------------------------------------------
    def _normalize(self, text: str) -> str:
        # Unicode NFC normalization
        cleaned = unicodedata.normalize("NFC", text)

        # Remove zero-width characters
        cleaned = MicroRegex.ZERO_WIDTH.sub("", cleaned)

        # Normalize paragraphs
        cleaned = MicroParagraphNormalizer.normalize(cleaned)

        # Collapse repeated punctuation
        cleaned = re.sub(r"([!?.,])\1{1,}", r"\1", cleaned)

        return cleaned

    # ------------------------------------------------------------
    # INTERNAL: extract linguistic structure
    # ------------------------------------------------------------
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

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
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

            # Micro: normalize whitespace
            query = MicroStringStripper.clean(query)

            # Micro: limit size for speed
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            # Normalize
            cleaned = self._normalize(query)

            # Classify
            qtype = self._classify_query(cleaned)

            # Structure
            structure = self._extract_structure(cleaned)

            envelope = {
                "clarified_query": cleaned,
                "length": structure["tokens"],
                "query_type": qtype,
                "structure": structure,
            }

            # Cache
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


