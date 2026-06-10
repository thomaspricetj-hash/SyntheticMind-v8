from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
import zlib


# ------------------------------------------------------------
# 3D MEMORY STRUCTURE
# ------------------------------------------------------------
@dataclass
class Memory3D:
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
    def limit(text: str, max_chars: int = 4000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroLowerCache:
    __slots__ = ()
    @staticmethod
    def lower_list(items: List[str]) -> List[str]:
        return [i.lower() for i in items]


class MicroIntentScanner:
    __slots__ = ()
    @staticmethod
    def scan(lower: List[str]) -> List[str]:
        patterns = []

        if sum("fix" in r for r in lower) >= 2:
            patterns.append("user repeatedly asks for fixes")

        if sum("explain" in r for r in lower) >= 2:
            patterns.append("user repeatedly asks for explanations")

        if sum("error" in r for r in lower) >= 2:
            patterns.append("multiple past errors detected")

        return patterns


class MicroContradictionScanner:
    __slots__ = ()
    @staticmethod
    def scan(recalled: List[str]) -> List[str]:
        contradictions = []
        for r in recalled:
            rl = r.lower()
            if "not" in rl and (" is " in rl or " are " in rl):
                contradictions.append(f"possible contradiction: {r}")
        return contradictions


# ------------------------------------------------------------
# MAIN HELPER (3D-AWARE)
# ------------------------------------------------------------
class MemoryHelper:
    """
    Ultra-fast MemoryHelper with integrated micro-helpers and 3D structural view.
    """

    def __init__(self, memory) -> None:
        self.memory = memory
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: semantic recall (if supported)
    # ------------------------------------------------------------
    def _semantic_recall(self, query: str, top_k: int = 5) -> List[str]:
        if hasattr(self.memory, "semantic_recall"):
            try:
                return self.memory.semantic_recall(query, top_k=top_k)
            except Exception:
                return []
        return []

    # ------------------------------------------------------------
    # INTERNAL: build 3D memory envelope
    # ------------------------------------------------------------
    def _build_3d(self, query: str, literal: List[str], semantic: List[str], signals: Dict[str, Any]) -> Memory3D:
        lines = query.splitlines()
        axis_z = {
            "literal": literal,
            "semantic": semantic,
            "signals": signals,
        }
        return Memory3D(
            raw_query=query,
            axis_x=query,
            axis_y=lines,
            axis_z=axis_z,
        )

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def recall(self, query: str) -> Dict[str, Any]:
        try:
            query = (query or "").strip()
            if not query:
                empty_signals = {
                    "repeated_intents": [],
                    "contradictions": [],
                }
                return {
                    "literal": [],
                    "semantic": [],
                    "signals": empty_signals,
                    "structure_3d": self._build_3d("", [], [], empty_signals),
                }

            # Micro: normalize
            query = MicroStringStripper.clean(query)

            # Micro: limit size
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            # Literal recall
            literal = self.memory.recall(query, top_k=5) or []

            # Semantic recall
            semantic = self._semantic_recall(query, top_k=5)

            # Combine for signal analysis
            combined = literal + semantic

            # Micro: pre-lowercase
            lower = MicroLowerCache.lower_list(combined)

            # Micro: repeated intent detection
            repeated = MicroIntentScanner.scan(lower)

            # Micro: contradiction detection
            contradictions = MicroContradictionScanner.scan(combined)

            signals = {
                "repeated_intents": repeated,
                "contradictions": contradictions,
            }

            structure_3d = self._build_3d(query, literal, semantic, signals)

            envelope = {
                "literal": literal,
                "semantic": semantic,
                "signals": signals,
                "structure_3d": structure_3d,
            }

            # Cache
            self.cache[h] = envelope
            return envelope

        except Exception as e:
            empty_signals = {
                "repeated_intents": [],
                "contradictions": [],
            }
            return {
                "literal": [],
                "semantic": [],
                "signals": empty_signals,
                "structure_3d": self._build_3d(query or "", [], [], empty_signals),
                "error": str(e),
            }

