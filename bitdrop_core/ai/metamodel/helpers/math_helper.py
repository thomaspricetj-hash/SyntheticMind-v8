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
# MAIN HELPER (STRUCTURED MATH REASONING, MAX 3D)
# ------------------------------------------------------------
class MathHelper:
    """
    Upgraded MathHelper (MAX 3D Version)

    Produces strict, 4-section, domain-oriented mathematical reasoning
    suitable for multi-pass, 3D tensor-based thinking.

    Output format (from process):
        {
            "text": "<full structured answer>",
            "sections": ["Definitions", "Derivation", "Conditions", "Final Answer"],
            "domain": "math",
            "valid": True/False,
            "raw_query": "<normalized query>",
            "tokens": {...},
            "math_domain": "<algebra|calculus|...>"
        }
    """

    ALGEBRA_KEYWORDS = [
        "solve", "equation", "variable", "factor", "polynomial",
        "quadratic", "root", "system of equations",
    ]

    CALCULUS_KEYWORDS = [
        "derivative", "integral", "limit", "gradient", "divergence",
        "partial derivative", "differential", "antiderivative",
    ]

    PROBABILITY_KEYWORDS = [
        "probability", "distribution", "random", "expectation",
        "variance", "bayes", "stochastic",
    ]

    LINEAR_ALGEBRA_KEYWORDS = [
        "matrix", "vector", "eigenvalue", "eigenvector",
        "transpose", "determinant", "rank",
    ]

    ARITHMETIC_OPERATORS = ["+", "-", "*", "/", "^", "=", "%"]

    def __init__(self) -> None:
        # Per-helper cache keyed by fast hash of normalized query
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: detect math intent (used to mark valid)
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
    # PUBLIC: main entrypoint (1D)
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Structured math reasoning entry point.

        Keeps original signature for compatibility with MathHelper3D
        and any existing callers.
        """
        try:
            query = (query or "").strip()
            if not query:
                return {
                    "text": "",
                    "sections": [],
                    "domain": "math",
                    "valid": False,
                    "raw_query": "",
                    "tokens": {},
                    "math_domain": "unknown",
                }

            # Normalize + limit
            norm = MicroStringStripper.clean(query)
            norm = MicroTokenLimiter.limit(norm)

            # Cache lookup
            h = MicroFastHash.h(norm)
            cached = self.cache.get(h)
            if cached is not None:
                return cached

            detected = self._detect_math(norm)
            math_domain = self._classify_domain(norm)
            tokens = self._extract_tokens(norm)

            # If it's clearly not math, mark invalid but still structured
            if not detected:
                env = {
                    "text": "",
                    "sections": [],
                    "domain": "math",
                    "valid": False,
                    "raw_query": norm,
                    "tokens": tokens,
                    "math_domain": math_domain,
                }
                self.cache[h] = env
                return env

            definitions = self._build_definitions(norm, tokens, math_domain)
            derivation = self._build_derivation(norm, tokens, math_domain)
            conditions = self._build_conditions(norm, tokens, math_domain)
            final_answer = self._build_final_answer(norm, tokens, math_domain)

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
                "domain": "math",
                "valid": True,
                "raw_query": norm,
                "tokens": tokens,
                "math_domain": math_domain,
            }

            self.cache[h] = env
            return env

        except Exception as e:
            norm = MicroStringStripper.clean(query or "")
            norm = MicroTokenLimiter.limit(norm)
            h = MicroFastHash.h(norm)
            env = {
                "text": f"[MathHelperError] {e}",
                "sections": [],
                "domain": "math",
                "valid": False,
                "raw_query": norm,
                "tokens": {},
                "math_domain": "error",
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
        tokens: Dict[str, List[str]],
        math_domain: str,
    ) -> str:
        lines: List[str] = []

        if tokens.get("numbers"):
            lines.append("• Numbers detected: " + ", ".join(tokens["numbers"]) + ".")

        if tokens.get("operators"):
            lines.append("• Operators detected: " + ", ".join(tokens["operators"]) + ".")

        lines.append("• Identify all variables and constants appearing in the problem.")
        lines.append("• State the type of mathematical object involved (e.g., scalar, vector, matrix, function).")

        if math_domain == "algebra":
            lines.append("• Clarify which symbols are unknowns and which are parameters in the algebraic equation(s).")
        elif math_domain == "calculus":
            lines.append("• Specify the function(s) involved and the variable(s) of differentiation or integration.")
        elif math_domain == "probability":
            lines.append("• Define random variables, their distributions, and any parameters (mean, variance, etc.).")
        elif math_domain == "linear_algebra":
            lines.append("• Define the dimensions of matrices/vectors and any relevant subspaces.")
        elif math_domain == "arithmetic":
            lines.append("• Clarify the intended numeric operations and any implied grouping (precedence).")
        else:
            lines.append("• Clarify the general mathematical context if not obvious (algebra, calculus, etc.).")

        return "\n".join(lines)

    def _build_derivation(
        self,
        query: str,
        tokens: Dict[str, List[str]],
        math_domain: str,
    ) -> str:
        lines: List[str] = []

        if math_domain == "algebra":
            lines.append("• Write the equation(s) explicitly and bring all terms to one side if solving for roots.")
            lines.append("• Simplify expressions (combine like terms, factor where possible).")
            lines.append("• Isolate the unknown step by step, justifying each algebraic manipulation.")
        elif math_domain == "calculus":
            lines.append("• Identify whether the task is differentiation, integration, or limit evaluation.")
            lines.append("• Apply the appropriate rules (product, chain, quotient, substitution, etc.).")
            lines.append("• Show intermediate steps rather than jumping directly to the final expression.")
        elif math_domain == "probability":
            lines.append("• Express the desired probability or expectation in terms of integrals or sums.")
            lines.append("• Use known distributions, laws (e.g., total probability, Bayes), or transformations.")
            lines.append("• Simplify the resulting expression carefully, keeping track of normalization.")
        elif math_domain == "linear_algebra":
            lines.append("• Write the matrix/vector equations explicitly.")
            lines.append("• Apply row operations, eigenvalue equations, or other relevant transformations step by step.")
            lines.append("• Justify rank, independence, or diagonalization claims with explicit reasoning.")
        elif math_domain == "arithmetic":
            lines.append("• Apply operator precedence (PEMDAS) explicitly.")
            lines.append("• Evaluate step by step, showing intermediate numeric results.")
        else:
            lines.append("• Rewrite the problem in a clear mathematical form.")
            lines.append("• Proceed with the most natural derivation path (algebraic, calculus, etc.), showing each step.")

        lines.append("• At each step, check that transformations are logically valid and reversible when required.")

        return "\n".join(lines)

    def _build_conditions(
        self,
        query: str,
        tokens: Dict[str, List[str]],
        math_domain: str,
    ) -> str:
        lines: List[str] = []

        lines.append("• State any domain restrictions on variables (e.g., x ≠ 0, x > 0, probabilities in [0, 1]).")
        lines.append("• Identify assumptions such as continuity, differentiability, or integrability where needed.")
        lines.append("• If solving equations, state conditions under which solutions exist and are unique.")
        if math_domain == "probability":
            lines.append("• Ensure probabilities sum/integrate to 1 and remain within [0, 1].")
        if math_domain == "linear_algebra":
            lines.append("• State conditions on matrix rank, invertibility, or eigenvalue properties.")
        if math_domain == "calculus":
            lines.append("• Clarify limits of integration and convergence of improper integrals if present.")

        lines.append("• Note any approximations or series expansions used and their validity range.")

        return "\n".join(lines)

    def _build_final_answer(
        self,
        query: str,
        tokens: Dict[str, List[str]],
        math_domain: str,
    ) -> str:
        lines: List[str] = []

        lines.append("• Present the final result in its simplest exact form (symbolic) when possible.")
        lines.append("• If a numeric approximation is required, provide it with a clear precision (e.g., 3 significant figures).")
        lines.append("• If multiple solutions exist, list all of them and indicate any that are extraneous.")
        lines.append("• If the problem is ill-posed or has no solution, state this explicitly and explain why.")
        lines.append("• Summarize the key mathematical insight or method used (e.g., factoring, substitution, eigen-decomposition).")

        return "\n".join(lines)


# ------------------------------------------------------------
# 3D MATH HELPER (MAXED, BACKWARD-COMPATIBLE)
# ------------------------------------------------------------
class MathHelper3D:
    """
    3D MathHelper:
        • Reuses MathHelper core logic
        • Adds 3D grids of queries: [D][H][W]
        • Per-cell math reasoning envelope
        • Cache amplification across 3D space
    """

    def __init__(self) -> None:
        self.helper = MathHelper()

    def process_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        queries_3d[d][h][w] = query string
        returns envelopes_3d[d][h][w] = MathHelper envelope
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
        Convenience: return only math_domain per cell.
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
                    row_out.append(env.get("math_domain", "unknown"))
                plane_out.append(row_out)
            out.append(plane_out)

        return out
