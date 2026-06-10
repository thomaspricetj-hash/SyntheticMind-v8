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
        ops: List[str] = []
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
# MAIN HELPER (STRUCTURED LOGIC REASONING, MAX 3D)
# ------------------------------------------------------------
class LogicHelper:
    """
    Upgraded LogicHelper (MAX 3D Version)

    Produces strict, 4-section, logic-oriented reasoning suitable for
    multi-pass, 3D tensor-based thinking.

    Output format (from process):
        {
            "text": "<full structured answer>",
            "sections": ["Definitions", "Derivation", "Conditions", "Final Answer"],
            "domain": "logic",
            "valid": True/False,
            "raw_query": "<normalized query>",
            "operators": [...],
            "logic_domain": "<formal_proof|contradiction|...>"
        }
    """

    DEDUCTIVE_KEYWORDS = [
        "therefore", "implies", "if and only if", "iff",
        "hence", "thus", "conclude", "deduce",
    ]

    PROOF_KEYWORDS = [
        "prove", "show that", "demonstrate", "assume", "contradiction",
        "lemma", "theorem", "corollary", "axiom",
    ]

    LOGIC_OPERATORS = [
        "→", "⇒", "⇔", "¬", "∧", "∨",
        "implies", "and", "or", "not",
    ]

    def __init__(self) -> None:
        # Per-helper cache keyed by fast hash of normalized query
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
    # PUBLIC: main entrypoint (1D)
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
                "text": "<4-section structured reasoning>",
                "sections": [...],
                "domain": "logic",
                "valid": bool,
                "raw_query": "...",
                "operators": [...],
                "logic_domain": "..."
            }

        Always returns the same structural shape; `valid` indicates
        whether the query was actually logical.
        """
        try:
            query = (query or "").strip()
            if not query:
                return {
                    "text": "",
                    "sections": [],
                    "domain": "logic",
                    "valid": False,
                    "raw_query": "",
                    "operators": [],
                    "logic_domain": "unknown",
                }

            # Normalize + limit
            norm = MicroStringStripper.clean(query)
            norm = MicroTokenLimiter.limit(norm)

            # Cache lookup
            h = MicroFastHash.h(norm)
            cached = self.cache.get(h)
            if cached is not None:
                return cached

            detected = self._detect_logic(norm)
            logic_domain = self._classify_domain(norm)
            operators = self._extract_operators(norm)

            definitions = self._build_definitions(norm, operators, logic_domain)
            derivation = self._build_derivation(norm, operators, logic_domain)
            conditions = self._build_conditions(norm, operators, logic_domain)
            final_answer = self._build_final_answer(norm, operators, logic_domain)

            text = (
                "[1] Definitions\n" + definitions + "\n\n"
                "[2] Derivation\n" + derivation + "\n\n"
                "[3] Conditions\n" + conditions + "\n\n"
                "[4] Final Answer\n" + final_answer
            )

            env: Dict[str, Any] = {
                "text": text,
                "sections": [
                    "Definitions",
                    "Derivation",
                    "Conditions",
                    "Final Answer",
                ],
                "domain": "logic",
                "valid": bool(detected),
                "raw_query": norm,
                "operators": operators,
                "logic_domain": logic_domain,
            }

            self.cache[h] = env
            return env

        except Exception as e:
            norm = MicroStringStripper.clean(query or "")
            norm = MicroTokenLimiter.limit(norm)
            h = MicroFastHash.h(norm)
            env = {
                "text": f"[LogicHelperError] {e}",
                "sections": [],
                "domain": "logic",
                "valid": False,
                "raw_query": norm,
                "operators": [],
                "logic_domain": "error",
                "error": str(e),
            }
            self.cache[h] = env
            return env

    # ------------------------------------------------------------
    # INTERNAL STRUCTURED BUILDERS
    # ------------------------------------------------------------
    def _build_definitions(
        self,
        query: str,
        operators: List[str],
        logic_domain: str,
    ) -> str:
        lines: List[str] = []

        if operators:
            lines.append("• Logical operators detected: " + ", ".join(operators) + ".")

        lines.append("• Identify all propositions or statements involved (label them as P, Q, R, etc.).")
        lines.append("• Clarify the meaning of each proposition in plain language.")
        lines.append("• Distinguish between assumptions/premises and the target conclusion.")

        if logic_domain == "formal_proof":
            lines.append("• Treat the setting as a formal proof with explicit premises and a goal statement.")
        elif logic_domain == "contradiction":
            lines.append("• Identify the statements that are suspected to be mutually inconsistent.")
        elif logic_domain == "equivalence":
            lines.append("• Identify the two statements claimed to be equivalent (A and B).")
        elif logic_domain == "deduction":
            lines.append("• Identify the premises and the intended conclusion of the deduction.")
        elif logic_domain == "assumption_based":
            lines.append("• Identify which statements are assumed temporarily and which are global premises.")
        else:
            lines.append("• Clarify the general logical context if not obvious (proof, equivalence, contradiction, etc.).")

        return "\n".join(lines)

    def _build_derivation(
        self,
        query: str,
        operators: List[str],
        logic_domain: str,
    ) -> str:
        lines: List[str] = []

        if logic_domain == "formal_proof":
            lines.append("• Start from the given premises and apply valid inference rules step by step.")
            lines.append("• Use standard rules (modus ponens, modus tollens, conjunction, disjunction, etc.) explicitly.")
            lines.append("• Avoid skipping steps; show how each line follows from previous ones.")
        elif logic_domain == "contradiction":
            lines.append("• Assume the negation of the desired conclusion (or a key statement).")
            lines.append("• Derive consequences until a clear contradiction is obtained (P and ¬P).")
            lines.append("• Conclude that the assumption must be false, so the original statement holds.")
        elif logic_domain == "equivalence":
            lines.append("• Prove A ⇒ B by assuming A and deriving B.")
            lines.append("• Prove B ⇒ A by assuming B and deriving A.")
            lines.append("• Conclude A ⇔ B once both directions are established.")
        elif logic_domain == "deduction":
            lines.append("• List the premises explicitly and derive the conclusion using valid inference rules.")
            lines.append("• Check that no step introduces information not justified by the premises.")
        elif logic_domain == "assumption_based":
            lines.append("• Mark which steps depend on temporary assumptions.")
            lines.append("• Show how discharging assumptions leads to the final conclusion.")
        else:
            lines.append("• Rewrite the argument in a clear premise–conclusion structure.")
            lines.append("• Apply standard inference rules to move from premises to conclusion.")

        lines.append("• At each step, ensure that no fallacies (e.g., affirming the consequent, denying the antecedent) are used.")

        return "\n".join(lines)

    def _build_conditions(
        self,
        query: str,
        operators: List[str],
        logic_domain: str,
    ) -> str:
        lines: List[str] = []

        lines.append("• State all assumptions explicitly, including any hidden or implicit premises.")
        lines.append("• Clarify whether the reasoning is classical, intuitionistic, or another logical system if relevant.")
        lines.append("• Identify any use of excluded middle, double negation, or other system-specific principles.")
        lines.append("• Check whether the argument depends on domain-specific facts (e.g., about numbers, sets) beyond pure logic.")
        lines.append("• Note any conditions under which the argument would fail (e.g., if a premise is false).")

        return "\n".join(lines)

    def _build_final_answer(
        self,
        query: str,
        operators: List[str],
        logic_domain: str,
    ) -> str:
        lines: List[str] = []

        lines.append("• State clearly whether the conclusion logically follows from the premises.")
        lines.append("• If the argument is invalid, specify exactly where the reasoning breaks.")
        lines.append("• If a contradiction was derived, state the contradictory pair explicitly (P and ¬P).")
        lines.append("• If an equivalence was proven, restate it as A ⇔ B with a brief justification.")
        lines.append("• Summarize the overall logical structure in one or two precise sentences (e.g., proof by contradiction, direct proof).")

        return "\n".join(lines)


# ------------------------------------------------------------
# 3D LOGIC HELPER (MAXED, BACKWARD-COMPATIBLE)
# ------------------------------------------------------------
class LogicHelper3D:
    """
    3D LogicHelper:
        • Reuses LogicHelper core logic
        • Adds 3D grids of queries: [D][H][W]
        • Per-cell logic reasoning envelope
        • Cache amplification across 3D space
    """

    def __init__(self) -> None:
        self.helper = LogicHelper()

    def process_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        queries_3d[d][h][w] = query string
        returns envelopes_3d[d][h][w] = LogicHelper envelope
        """
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(self.helper.process(q, lang_info, memory_info))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def domain_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[str]]]:
        """
        Convenience: return only logic_domain per cell.
        """
        envelopes_3d = self.process_3d(queries_3d, lang_info, memory_info)
        depth = len(envelopes_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = envelopes_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for env in row:
                    row_out.append(env.get("logic_domain", "unknown"))
                plane_out.append(row_out)
            out.append(plane_out)

        return out
