from __future__ import annotations
from typing import Any, Dict, List
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
    def limit(text: str, max_chars: int = 6000) -> str:
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
    NUMBERS = re.compile(r"[-+]?\d*\.\d+|[-+]?\d+")
    SENTENCES = re.compile(r"[.!?]+")


class MicroMathClassifier:
    __slots__ = ()
    @staticmethod
    def classify(text: str) -> str:
        t = text.lower()

        if any(k in t for k in (
            "derivative", "integral", "limit", "gradient",
            "divergence", "partial derivative", "antiderivative"
        )):
            return "calculus"

        if any(k in t for k in (
            "solve", "equation", "variable", "factor",
            "polynomial", "quadratic", "root", "system of equations"
        )):
            return "algebra"

        if any(k in t for k in (
            "probability", "distribution", "random", "expectation",
            "variance", "bayes", "stochastic"
        )):
            return "probability"

        if any(k in t for k in (
            "matrix", "vector", "eigenvalue", "eigenvector",
            "transpose", "determinant", "rank"
        )):
            return "linear_algebra"

        if any(op in text for op in ["+", "-", "*", "/", "^", "=", "%"]):
            return "arithmetic"

        return "unknown"


class MicroTokenExtractor:
    __slots__ = ()
    @staticmethod
    def extract(text: str, ops: List[str]) -> Dict[str, List[str]]:
        numbers = MicroRegex.NUMBERS.findall(text)
        operators = [op for op in ops if op in text]
        return {"numbers": numbers, "operators": operators}


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class MathHelper:
    """
    Ultra-fast MathHelper with integrated micro-helpers.
    """

    ALGEBRA_KEYWORDS = [
        "solve", "equation", "variable", "factor", "polynomial",
        "quadratic", "root", "system of equations"
    ]

    CALCULUS_KEYWORDS = [
        "derivative", "integral", "limit", "gradient", "divergence",
        "partial derivative", "differential", "antiderivative"
    ]

    PROBABILITY_KEYWORDS = [
        "probability", "distribution", "random", "expectation",
        "variance", "bayes", "stochastic"
    ]

    LINEAR_ALGEBRA_KEYWORDS = [
        "matrix", "vector", "eigenvalue", "eigenvector",
        "transpose", "determinant", "rank"
    ]

    ARITHMETIC_OPERATORS = ["+", "-", "*", "/", "^", "=", "%"]

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: detect math intent
    # ------------------------------------------------------------
    def _detect_math(self, query: str) -> bool:
        q = query.lower()

        if any(op in query for op in self.ARITHMETIC_OPERATORS):
            return True

        if any(kw in q for kw in (
            self.ALGEBRA_KEYWORDS
            + self.CALCULUS_KEYWORDS
            + self.PROBABILITY_KEYWORDS
            + self.LINEAR_ALGEBRA_KEYWORDS
        )):
            return True

        if re.search(r"\d", query):
            return True

        return False

    # ------------------------------------------------------------
    # INTERNAL: classify math domain
    # ------------------------------------------------------------
    def _classify_domain(self, query: str) -> str:
        return MicroMathClassifier.classify(query)

    # ------------------------------------------------------------
    # INTERNAL: extract numbers and operators
    # ------------------------------------------------------------
    def _extract_tokens(self, query: str) -> Dict[str, List[str]]:
        return MicroTokenExtractor.extract(query, self.ARITHMETIC_OPERATORS)

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            query = (query or "").strip()
            if not query:
                return {"detected": False}

            # Micro: normalize
            query = MicroStringStripper.clean(query)

            # Micro: limit size
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            detected = self._detect_math(query)
            if not detected:
                return {"detected": False}

            domain = self._classify_domain(query)
            tokens = self._extract_tokens(query)

            notes: List[str] = []

            if domain == "arithmetic":
                notes.append("Arithmetic: consider operator precedence (PEMDAS).")
                notes.append("Arithmetic: check for integer vs float behavior.")

            elif domain == "algebra":
                notes.append("Algebra: isolate variables, simplify expressions.")
                notes.append("Algebra: consider factoring or quadratic formula if applicable.")

            elif domain == "calculus":
                notes.append("Calculus: identify derivative/integral structure.")
                notes.append("Calculus: check continuity, limits, and symbolic simplification.")

            elif domain == "probability":
                notes.append("Probability: identify distributions and random variables.")
                notes.append("Probability: consider expectation, variance, and Bayes relationships.")

            elif domain == "linear_algebra":
                notes.append("Linear algebra: consider matrix operations and eigenstructure.")
                notes.append("Linear algebra: check dimensionality and rank conditions.")

            else:
                notes.append("Math detected but domain unclear — fallback to general reasoning.")

            envelope = {
                "detected": True,
                "domain": domain,
                "tokens": tokens,
                "raw_query": query,
                "notes": notes,
            }

            # Cache
            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "detected": True,
                "domain": "error",
                "tokens": {},
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }


