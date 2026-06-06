from __future__ import annotations
from typing import Any, Dict, List
import math
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


class MicroPhraseScanner:
    __slots__ = ()
    @staticmethod
    def scan(words: List[str]) -> List[str]:
        if len(words) < 4:
            return []

        phrases = {}
        # 2–4 word phrases
        for size in (2, 3, 4):
            for i in range(len(words) - size + 1):
                ph = " ".join(words[i:i + size])
                phrases[ph] = phrases.get(ph, 0) + 1

        return [p for p, c in phrases.items() if c >= 2][:10]


class MicroOverlapScanner:
    __slots__ = ()
    @staticmethod
    def scan(text: str, memory_info: Dict[str, Any]) -> List[str]:
        overlaps = []
        literal = memory_info.get("literal", [])
        semantic = memory_info.get("semantic", [])

        for item in literal:
            if item and item in text:
                overlaps.append(item)

        for item in semantic:
            if item and item in text:
                overlaps.append(item)

        return overlaps[:10]


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class CompressionHelper:
    """
    Ultra-fast semantic compression helper with micro-helpers.
    """

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: entropy estimation
    # ------------------------------------------------------------
    def _entropy(self, text: str) -> float:
        if not text:
            return 0.0

        freq = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1

        length = len(text)
        entropy = 0.0

        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)

        return round(entropy, 4)

    # ------------------------------------------------------------
    # INTERNAL: detect repeated patterns
    # ------------------------------------------------------------
    def _detect_repeated_phrases(self, text: str) -> List[str]:
        words = text.split()
        return MicroPhraseScanner.scan(words)

    # ------------------------------------------------------------
    # INTERNAL: detect structural complexity
    # ------------------------------------------------------------
    def _complexity_score(self, text: str) -> float:
        tokens = text.split()
        symbols = MicroRegex.SYMBOLS.findall(text)
        sentences = [s for s in MicroRegex.SENTENCES.split(text) if s.strip()]

        score = (
            len(tokens) * 0.4 +
            len(symbols) * 0.3 +
            len(sentences) * 0.3
        )

        return round(score, 3)

    # ------------------------------------------------------------
    # INTERNAL: detect redundancy with memory
    # ------------------------------------------------------------
    def _memory_overlap(self, text: str, memory_info: Dict[str, Any]) -> List[str]:
        return MicroOverlapScanner.scan(text, memory_info)

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(self, query: str, lang_info: Dict[str, Any], memory_info: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Micro: normalize
            query = MicroStringStripper.clean(query)

            # Micro: limit size for speed
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            entropy = self._entropy(query)
            repeated = self._detect_repeated_phrases(query)
            complexity = self._complexity_score(query)
            overlap = self._memory_overlap(query, memory_info)

            envelope = {
                "entropy": entropy,
                "repeated_phrases": repeated,
                "complexity": complexity,
                "memory_overlap": overlap,
                "raw_query": query,
                "notes": [
                    f"Entropy: {entropy}",
                    f"Complexity: {complexity}",
                    f"Repeated phrases: {len(repeated)}",
                    f"Memory overlap: {len(overlap)}",
                ],
            }

            # Micro: cache
            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "entropy": 0.0,
                "repeated_phrases": [],
                "complexity": 0.0,
                "memory_overlap": [],
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }


        for mem in literal + semantic:
            if not isinstance(mem, str):
                continue
            if mem and mem.lower() in text.lower():
                overlaps.append(mem)

        return overlaps[:10]

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Returns a structured semantic-compression envelope:
            {
                "hint": "ok_to_compress",
                "entropy": float,
                "complexity": float,
                "repeated_phrases": [...],
                "memory_overlap": [...],
                "raw_query": "...",
            }
        """
        try:
            cleaned = lang_info.get("clarified_query", query)

            entropy = self._entropy(cleaned)
            complexity = self._complexity_score(cleaned)
            repeated = self._detect_repeated_phrases(cleaned)
            overlap = self._memory_overlap(cleaned, memory_info)

            return {
                "hint": "ok_to_compress",
                "entropy": entropy,
                "complexity": complexity,
                "repeated_phrases": repeated,
                "memory_overlap": overlap,
                "raw_query": cleaned,
            }

        except Exception as e:
            # Fail-soft
            return {
                "hint": "ok_to_compress",
                "entropy": 0.0,
                "complexity": 0.0,
                "repeated_phrases": [],
                "memory_overlap": [],
                "raw_query": query,
                "error": str(e),
            }

