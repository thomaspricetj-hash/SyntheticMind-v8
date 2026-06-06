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
    SYMBOLIC_OPS = re.compile(r"[¬∧∨→⇒⇔]")
    SENTENCES = re.compile(r"[.!?]+")


class MicroLogicClassifier:
    __slots__ = ()
    @staticmethod
    def classify(text: str) -> str:
        t = text.lower()

        if any(k in t for k in ("prove", "lemma", "theorem", "corollary", "axiom")):
            return "formal_proof"

        if "contradiction" in t or "not both" in t:
            return "contradiction"

        if "iff" in t or "if and only if" in t or "equivalent" in t:
            return "equivalence"

        if any(k in t for k in ("therefore", "hence", "thus", "deduce", "implies")):
            return "deduction"

        if "assume" in t or "suppose" in t:
            return "assumption_based"

        return "unknown"


class MicroOperatorScanner:
    __slots__ = ()
    @staticmethod
    def scan(text: str, logic_ops: List[str]) -> List[str]:
        ops = []
        t = text.lower()

        # Word operators
        for op in logic_ops:
            if op in t:
                ops.append(op)

        # Symbolic operators
        symbolic = MicroRegex.SYMBOLIC_OPS.findall(text)
        ops.extend(symbolic)

        # Deduplicate while preserving order
        return list(dict.fromkeys(ops))


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class LogicHelper:
    """
    Ultra-fast LogicHelper with integrated micro-helpers.
    """

    DEDUCTIVE_KEYWORDS = [
        "therefore", "implies", "if and only if", "iff",
        "hence", "thus", "conclude", "deduce"
    ]

    PROOF_KEYWORDS = [
        "prove", "show that", "demonstrate", "assume", "contradiction",
        "lemma", "theorem", "corollary", "axiom"
    ]

    LOGIC_OPERATORS = [
        "→", "⇒", "⇔", "¬", "∧", "∨",
        "implies", "and", "or", "not"
    ]

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: detect logic intent
    # ------------------------------------------------------------
    def _detect_logic(self, query: str) -> bool:
        q = query.lower()

        if any(kw in q for kw in self.DEDUCTIVE_KEYWORDS):
            return True

        if any(kw in q for kw in self.PROOF_KEYWORDS):
            return True

        if any(op in q for op in self.LOGIC_OPERATORS):
            return True

        return False

    # ------------------------------------------------------------
    # INTERNAL: classify logic domain
    # ------------------------------------------------------------
    def _classify_domain(self, query: str) -> str:
        return MicroLogicClassifier.classify(query)

    # ------------------------------------------------------------
    # INTERNAL: extract logical operators
    # ------------------------------------------------------------
    def _extract_operators(self, query: str) -> List[str]:
        return MicroOperatorScanner.scan(query, self.LOGIC_OPERATORS)

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(self, query: str, lang_info: Dict[str, Any], memory_info: Dict[str, Any]) -> Dict[str, Any]:
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

            detected = self._detect_logic(query)
            if not detected:
                return {"detected": False}

            domain = self._classify_domain(query)
            operators = self._extract_operators(query)

            notes: List[str] = []

            if domain == "formal_proof":
                notes.append("Formal proof: identify assumptions, lemmas, and logical steps.")
            elif domain == "contradiction":
                notes.append("Contradiction: assume the negation and derive inconsistency.")
            elif domain == "equivalence":
                notes.append("Equivalence: prove both directions independently.")
            elif domain == "deduction":
                notes.append("Deduction: apply logical implications and inference rules.")
            elif domain == "assumption_based":
                notes.append("Assumption-based: track assumptions and derived consequences.")
            else:
                notes.append("Logic detected but domain unclear — fallback to general reasoning.")

            envelope = {
                "detected": True,
                "domain": domain,
                "operators": operators,
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
                "operators": [],
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }

    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Returns a structured logic reasoning envelope:
            {
                "detected": bool,
                "domain": "...",
                "operators": [...],
                "raw_query": "...",
                "notes": [...],
            }
        """
        try:
            detected = self._detect_logic(query)
            if not detected:
                return {"detected": False}

            domain = self._classify_domain(query)
            operators = self._extract_operators(query)

            notes: List[str] = []

            if domain == "formal_proof":
                notes.append("Logic: treat as a formal proof; identify assumptions and target statement.")
                notes.append("Logic: consider direct proof, contradiction, or contrapositive.")

            elif domain == "contradiction":
                notes.append("Logic: check for mutually exclusive statements or negations.")
                notes.append("Logic: consider reductio ad absurdum structure.")

            elif domain == "equivalence":
                notes.append("Logic: show both directions (A ⇒ B and B ⇒ A).")
                notes.append("Logic: identify shared invariants or transformations.")

            elif domain == "deduction":
                notes.append("Logic: identify premises and derive conclusions step-by-step.")
                notes.append("Logic: check for hidden assumptions.")

            elif domain == "assumption_based":
                notes.append("Logic: treat assumptions as temporary scaffolding.")
                notes.append("Logic: check if assumptions lead to contradictions or conclusions.")

            else:
                notes.append("Logic detected but domain unclear — fallback to general reasoning.")

            return {
                "detected": True,
                "domain": domain,
                "operators": operators,
                "raw_query": query,
                "notes": notes,
            }

        except Exception as e:
            # Fail-soft
            return {
                "detected": True,
                "domain": "error",
                "operators": [],
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }

