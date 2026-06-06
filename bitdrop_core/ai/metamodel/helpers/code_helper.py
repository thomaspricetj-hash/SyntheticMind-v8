from __future__ import annotations
from typing import Any, Dict, List
import re
import zlib


# ------------------------------------------------------------
# MICRO HELPERS (INLINE, ZERO OVERHEAD)
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()
    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.split())


class MicroEarlyExit:
    __slots__ = ()
    @staticmethod
    def check(text: str):
        t = text.lower()
        if len(t) <= 2:
            return True
        if t in ("ok", "yes", "no", "hi", "hey"):
            return True
        return False


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroTokenLimiter:
    __slots__ = ()
    @staticmethod
    def limit(text: str, max_chars: int = 5000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroBranchPredictor:
    __slots__ = ()
    @staticmethod
    def predict(text: str) -> str:
        t = text.lower()
        if "error" in t or "traceback" in t:
            return "debug"
        if "refactor" in t or "clean" in t:
            return "refactor"
        if "explain" in t:
            return "explain"
        if "generate" in t or "write code" in t:
            return "generate"
        return "unknown"


# ------------------------------------------------------------
# PRECOMPILED REGEX (FASTER)
# ------------------------------------------------------------
FENCED_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)
INLINE_RE = re.compile(r"`([^`]+)`")


class CodeHelper:
    """
    Ultra-fast CodeHelper with integrated micro-helpers.
    """

    LANG_PATTERNS = {
        "python": [r"\bdef\b", r"\bimport\b", r":\s*$", r"self"],
        "javascript": [r"\bfunction\b", r"console\.log", r"=>"],
        "typescript": [r"\binterface\b", r"\btype\b", r"=>"],
        "c++": [r"#include", r"\bstd::", r";\s*$"],
        "rust": [r"\blet\b", r"\bfn\b", r"::"],
        "go": [r"\bfunc\b", r"\bpackage\b"],
        "java": [r"\bclass\b", r"System\.out"],
        "bash": [r"#!/bin/bash", r"\becho\b"],
    }

    DEBUG_HINTS = ["fix", "error", "bug", "traceback", "exception", "crash"]
    REFACTOR_HINTS = ["refactor", "clean", "optimize", "improve"]
    EXPLAIN_HINTS = ["explain", "what does this do", "describe"]
    GENERATE_HINTS = ["write code", "generate", "create function", "implement"]

    def __init__(self):
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: detect code intent
    # ------------------------------------------------------------
    def _detect_code(self, query: str) -> bool:
        # Fenced code
        if "```" in query:
            return True

        # Inline indicators
        if any(sym in query for sym in ["{", "}", "();", "=>", "def ", "class "]):
            return True

        # Language patterns
        for patterns in self.LANG_PATTERNS.values():
            for p in patterns:
                if re.search(p, query):
                    return True

        return False

    # ------------------------------------------------------------
    # INTERNAL: extract code blocks
    # ------------------------------------------------------------
    def _extract_code(self, query: str) -> List[str]:
        blocks = []

        # Fenced
        fenced = FENCED_RE.findall(query)
        blocks.extend([b.strip() for b in fenced])

        # Inline
        inline = INLINE_RE.findall(query)
        blocks.extend([b.strip() for b in inline])

        return blocks

    # ------------------------------------------------------------
    # INTERNAL: detect programming language
    # ------------------------------------------------------------
    def _detect_language(self, code: str) -> str:
        for lang, patterns in self.LANG_PATTERNS.items():
            for p in patterns:
                if re.search(p, code):
                    return lang
        return "unknown"

    # ------------------------------------------------------------
    # INTERNAL: classify code intent
    # ------------------------------------------------------------
    def _classify_intent(self, query: str) -> str:
        q = query.lower()

        if any(h in q for h in self.DEBUG_HINTS):
            return "debug"
        if any(h in q for h in self.REFACTOR_HINTS):
            return "refactor"
        if any(h in q for h in self.EXPLAIN_HINTS):
            return "explain"
        if any(h in q for h in self.GENERATE_HINTS):
            return "generate"

        return "unknown"

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(self, query: str, lang_info: Dict[str, Any], memory_info: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Micro: normalize
            query = MicroStringStripper.clean(query)

            # Micro: trivial skip
            if MicroEarlyExit.check(query):
                return {"detected": False}

            # Micro: limit size for regex speed
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            # Detect code
            detected = self._detect_code(query)
            if not detected:
                return {"detected": False}

            code_blocks = self._extract_code(query)
            language = "unknown"

            if code_blocks:
                language = self._detect_language("\n".join(code_blocks))

            # Micro: fast intent prediction
            intent = MicroBranchPredictor.predict(query)
            if intent == "unknown":
                intent = self._classify_intent(query)

            notes: List[str] = []

            if intent == "debug":
                notes.append("Debug: inspect error messages, stack traces, and failing lines.")
                notes.append("Debug: check for syntax errors, type mismatches, or undefined variables.")
            elif intent == "refactor":
                notes.append("Refactor: simplify logic, remove duplication, improve naming.")
                notes.append("Refactor: consider splitting large functions into smaller units.")
            elif intent == "explain":
                notes.append("Explain: break down code into steps and describe control flow.")
                notes.append("Explain: identify key variables, loops, and function calls.")
            elif intent == "generate":
                notes.append("Generate: identify required inputs, outputs, and constraints.")
                notes.append("Generate: consider idiomatic patterns for the detected language.")
            else:
                notes.append("Code detected but intent unclear — fallback to general reasoning.")

            envelope = {
                "detected": True,
                "intent": intent,
                "language": language,
                "code_blocks": code_blocks,
                "raw_query": query,
                "notes": notes,
            }

            # Micro: cache result
            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "detected": True,
                "intent": "error",
                "language": "unknown",
                "code_blocks": [],
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }

