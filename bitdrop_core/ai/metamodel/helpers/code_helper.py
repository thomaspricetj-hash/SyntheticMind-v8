from __future__ import annotations
from typing import Any, Dict, List
import re
import zlib
import os
import importlib.util

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


# ------------------------------------------------------------
# NEW HELPER: CODING PATTERN ANALYZER
# ------------------------------------------------------------
class CodingPatternHelper:
    """
    Detects common coding anti-patterns and quality issues.
    Lightweight and safe to run on any code block.
    """
    __slots__ = ()

    @staticmethod
    def analyze(code: str) -> List[str]:
        notes = []

        if code.count("\n") > 40:
            notes.append("Quality: Function or block is very long — consider splitting into smaller units.")

        if "    " * 4 in code:
            notes.append("Quality: Deep nesting detected — consider flattening logic or early returns.")

        if re.search(r"\b\d{2,}\b", code):
            notes.append("Quality: Magic numbers found — replace with named constants.")

        if "def " in code and '"""' not in code:
            notes.append("Quality: Function missing docstring — add a brief description of behavior.")

        if "import " in code:
            imports = re.findall(r"import (\w+)", code)
            for imp in imports:
                if imp not in code.split("import ")[-1]:
                    notes.append(f"Quality: Possible unused import '{imp}'.")

        if "def " in code and ":" not in code.split("def ")[-1]:
            notes.append("Quality: Missing type hints — add parameter and return type annotations.")

        if "return" in code and "pass" in code:
            notes.append("Quality: Unreachable code — 'pass' after return has no effect.")

        return notes


# ------------------------------------------------------------
# CODEHELPER ULTRA-PRO (STRUCTURED, MAX 3D)
# ------------------------------------------------------------
class CodeHelper:
    """
    CodeHelper Ultra-Pro (MAX 3D Version)

    Produces strict, 4-section, code-oriented reasoning suitable for
    multi-pass, 3D tensor-based thinking.

    Output format (from process):
        {
            "text": "<full structured answer>",
            "sections": ["Definitions", "Derivation", "Conditions", "Final Answer"],
            "domain": "code",
            "valid": True/False,
            "detected": True/False,
            "raw_query": "<normalized query>",
            "language": "<python|javascript|...>",
            "intent": "<debug|refactor|explain|generate|...>",
            "code_blocks": [...],
            "notes": [...]
        }
    """

    LANG_PATTERNS = {
        "python": [
            r"\bdef\b", r"\bimport\b", r":\s*$", r"self",
            r"\basync\b", r"\bawait\b", r"\bwith\b"
        ],
        "javascript": [
            r"\bfunction\b", r"console\.log", r"=>", r"\basync\b"
        ],
        "typescript": [
            r"\binterface\b", r"\btype\b", r"=>", r"\bimplements\b"
        ],
        "c++": [
            r"#include", r"\bstd::", r";\s*$", r"\btemplate\b"
        ],
        "rust": [
            r"\blet\b", r"\bfn\b", r"::", r"\bimpl\b"
        ],
        "go": [
            r"\bfunc\b", r"\bpackage\b", r"\bgo\b"
        ],
        "java": [
            r"\bclass\b", r"System\.out", r"\bpublic\b"
        ],
        "bash": [
            r"#!/bin/bash", r"\becho\b", r"\bfi\b"
        ],
    }

    DEBUG_HINTS = ["fix", "error", "bug", "traceback", "exception", "crash", "fails", "broken"]
    REFACTOR_HINTS = ["refactor", "clean", "optimize", "improve", "simplify"]
    EXPLAIN_HINTS = ["explain", "what does", "describe", "how does"]
    GENERATE_HINTS = ["write code", "generate", "create function", "implement", "build"]

    CONCEPTS = {
        "O1_space": {
            "explain": "Use the input array itself as storage. Mark presence by modifying values in-place.",
            "example": "nums[i] += n+1 marks presence of i+1 without extra arrays."
        },
        "two_pointer": {
            "explain": "Use two indices that move independently to scan or partition data.",
            "example": "l, r = 0, len(arr)-1 while l < r: ..."
        },
        "hash_map": {
            "explain": "A dictionary mapping keys to values in O(1) average time.",
            "example": "m = {}; m[key] = value"
        },
        "recursion": {
            "explain": "A function that calls itself to break a problem into smaller pieces.",
            "example": "def f(n): return 1 if n==0 else n*f(n-1)"
        },
        "dynamic_programming": {
            "explain": "Store results of subproblems to avoid recomputation.",
            "example": "dp[i] = dp[i-1] + dp[i-2]"
        },
        "big_o": {
            "explain": "Big-O describes how runtime or memory grows with input size.",
            "example": "O(n log n) for sorting, O(n) for scanning."
        },
        "immutability": {
            "explain": "Immutable objects cannot be changed after creation.",
            "example": "Python strings and tuples are immutable."
        },
        "side_effects": {
            "explain": "A function has side effects if it modifies external state.",
            "example": "Modifying a global variable inside a function."
        },
    }

    def __init__(self):
        self.cache: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------
    # INTERNAL: detection, extraction, classification
    # ------------------------------------------------------------
    def _detect_code(self, query: str) -> bool:
        if "```" in query:
            return True
        if any(sym in query for sym in ["{", "}", "();", "=>", "def ", "class "]):
            return True
        for patterns in self.LANG_PATTERNS.values():
            for p in patterns:
                if re.search(p, query):
                    return True
        return False

    def _extract_code(self, query: str) -> List[str]:
        blocks = []
        blocks.extend([b.strip() for b in FENCED_RE.findall(query)])
        blocks.extend([b.strip() for b in INLINE_RE.findall(query)])
        return blocks

    def _detect_language(self, code: str) -> str:
        for lang, patterns in self.LANG_PATTERNS.items():
            for p in patterns:
                if re.search(p, code):
                    return lang
        return "unknown"

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

    def _teach_missing_concepts(self, code: str) -> List[str]:
        notes = []

        if "hash" in code and "O(1)" in code:
            c = self.CONCEPTS["O1_space"]
            notes.append("Concept: O(1) space in-place marking")
            notes.append("Explanation: " + c["explain"])
            notes.append("Example: " + c["example"])

        if "def" in code and "(" in code and "return" in code and "recurs" in code:
            c = self.CONCEPTS["recursion"]
            notes.append("Concept: Proper recursion structure")
            notes.append("Explanation: " + c["explain"])
            notes.append("Example: " + c["example"])

        if "while True" in code:
            notes.append("Warning: Infinite loop risk — ensure termination conditions.")

        if "eval(" in code or "exec(" in code:
            notes.append("Security: Avoid eval/exec — unsafe and unnecessary.")

        return notes

    # ------------------------------------------------------------
    # INTERNAL: structured section builders
    # ------------------------------------------------------------
    def _build_definitions(
        self,
        query: str,
        language: str,
        intent: str,
        code_blocks: List[str],
    ) -> str:
        lines: List[str] = []

        lines.append(f"• Detected language: {language}.")
        lines.append(f"• Detected intent: {intent}.")
        if code_blocks:
            lines.append(f"• Number of code blocks detected: {len(code_blocks)}.")
        else:
            lines.append("• No explicit code blocks detected; treat query as code-related description or request.")

        lines.append("• Identify the main function, class, or module under discussion.")
        lines.append("• Clarify the inputs, outputs, and side effects of the relevant code.")
        lines.append("• List any external dependencies or modules the code relies on.")

        return "\n".join(lines)

    def _build_derivation(
        self,
        query: str,
        language: str,
        intent: str,
        code_blocks: List[str],
        notes: List[str],
    ) -> str:
        lines: List[str] = []

        if intent == "debug":
            lines.append("• Reconstruct the failing scenario: inputs, environment, and observed error.")
            lines.append("• Trace the control flow to the failing line or function.")
            lines.append("• Inspect variable values and types at critical points.")
            lines.append("• Hypothesize likely root causes and connect them to specific lines of code.")
        elif intent == "refactor":
            lines.append("• Identify duplicated logic, long functions, and deeply nested branches.")
            lines.append("• Propose a decomposition into smaller, well-named functions or methods.")
            lines.append("• Suggest improvements to naming, structure, and separation of concerns.")
        elif intent == "explain":
            lines.append("• Walk through the code step by step, describing control flow and data flow.")
            lines.append("• Explain the purpose of each major block or function in plain language.")
        elif intent == "generate":
            lines.append("• Restate the requirements: inputs, outputs, constraints, and edge cases.")
            lines.append("• Propose a high-level algorithm or design before writing code.")
        else:
            lines.append("• Interpret the query as a general code reasoning task (debug, refactor, explain, or generate).")
            lines.append("• Choose the most appropriate reasoning path based on context.")

        if notes:
            lines.append("• Additional analysis hints and quality notes:")
            for n in notes:
                lines.append("  - " + n)

        return "\n".join(lines)

    def _build_conditions(
        self,
        query: str,
        language: str,
        intent: str,
        code_blocks: List[str],
    ) -> str:
        lines: List[str] = []

        lines.append("• State any assumptions about the runtime environment (OS, Python/Node/Java version, etc.).")
        lines.append("• Clarify external systems or services the code interacts with (databases, APIs, files).")
        lines.append("• Note performance or memory constraints that the code must respect.")
        lines.append("• Identify security, safety, or robustness requirements (e.g., input validation, error handling).")
        lines.append("• If refactoring, state compatibility constraints (public API, behavior must remain unchanged).")

        return "\n".join(lines)

    def _build_final_answer(
        self,
        query: str,
        language: str,
        intent: str,
        code_blocks: List[str],
    ) -> str:
        lines: List[str] = []

        if intent == "debug":
            lines.append("• Summarize the most likely root cause of the bug in one or two sentences.")
            lines.append("• State the minimal, precise change needed to fix it.")
        elif intent == "refactor":
            lines.append("• Summarize the proposed refactoring strategy and its benefits.")
            lines.append("• Highlight any key functions or modules that should be created or renamed.")
        elif intent == "explain":
            lines.append("• Provide a concise explanation of what the code does overall.")
        elif intent == "generate":
            lines.append("• Summarize the intended implementation approach and key steps.")
        else:
            lines.append("• Provide a concise conclusion about the code-related task or question.")

        lines.append("• If there are multiple viable options, briefly compare them and recommend one.")
        lines.append("• If the query is not actually code-related, state that explicitly.")

        return "\n".join(lines)

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint (1D)
    # ------------------------------------------------------------
    def process(self, query: str, lang_info: Dict[str, Any], memory_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Structured code reasoning entry point.

        Keeps original signature for compatibility, but now returns a
        4-section structured envelope with metadata.
        """
        try:
            query = MicroStringStripper.clean(query or "")

            if MicroEarlyExit.check(query):
                return {
                    "text": "",
                    "sections": [],
                    "domain": "code",
                    "valid": False,
                    "detected": False,
                    "raw_query": query,
                    "language": "unknown",
                    "intent": "unknown",
                    "code_blocks": [],
                    "notes": [],
                }

            query = MicroTokenLimiter.limit(query)

            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            detected = self._detect_code(query)
            code_blocks = self._extract_code(query) if detected else []
            language = self._detect_language("\n".join(code_blocks)) if code_blocks else "unknown"

            intent = MicroBranchPredictor.predict(query)
            if intent == "unknown":
                intent = self._classify_intent(query)

            notes: List[str] = []

            # Concept teaching + pattern analysis
            for block in code_blocks:
                notes.extend(self._teach_missing_concepts(block))
            for block in code_blocks:
                notes.extend(CodingPatternHelper.analyze(block))

            # Build structured sections
            definitions = self._build_definitions(query, language, intent, code_blocks)
            derivation = self._build_derivation(query, language, intent, code_blocks, notes)
            conditions = self._build_conditions(query, language, intent, code_blocks)
            final_answer = self._build_final_answer(query, language, intent, code_blocks)

            text = (
                "[1] Definitions\n" + definitions + "\n\n"
                "[2] Derivation\n" + derivation + "\n\n"
                "[3] Conditions\n" + conditions + "\n\n"
                "[4] Final Answer\n" + final_answer
            )

            envelope: Dict[str, Any] = {
                "text": text,
                "sections": [
                    "Definitions",
                    "Derivation",
                    "Conditions",
                    "Final Answer",
                ],
                "domain": "code",
                "valid": bool(detected),
                "detected": bool(detected),
                "raw_query": query,
                "language": language,
                "intent": intent,
                "code_blocks": code_blocks,
                "notes": notes,
            }

            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "text": f"[CodeHelperError] {e}",
                "sections": [],
                "domain": "code",
                "valid": False,
                "detected": True,
                "raw_query": query,
                "language": "unknown",
                "intent": "error",
                "code_blocks": [],
                "notes": ["Internal CodeHelper error"],
                "error": str(e),
            }


# ------------------------------------------------------------
# PROFESSIONAL PLUGIN LOADER (INSTALLED)
# ------------------------------------------------------------
class PluginManager:
    """
    Professional plugin loader:
    - Loads .py files from a folder
    - Validates each exposes run()
    - Supports optional dependencies = ["pluginA"]
    - Executes plugins in dependency order
    - Detects cycles
    """

    def __init__(self, modules_path: str):
        self.modules_path = modules_path
        self.plugins: Dict[str, object] = {}
        self.dependencies: Dict[str, List[str]] = {}

    def load_all(self):
        for filename in os.listdir(self.modules_path):
            if filename.endswith(".py") and not filename.startswith("__"):
                path = os.path.join(self.modules_path, filename)
                name = os.path.splitext(filename)[0]
                self._load_plugin(name, path)

    def _load_plugin(self, name: str, path: str):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "run") or not callable(module.run):
            raise ValueError(f"Plugin '{name}' must define a callable run() function.")

        deps = getattr(module, "dependencies", [])
        if not isinstance(deps, list):
            raise ValueError(f"Plugin '{name}' dependencies must be a list.")

        self.plugins[name] = module
        self.dependencies[name] = deps

    def execute_all(self):
        executed = set()
        visiting = set()

        def execute(name: str):
            if name in executed:
                return
            if name in visiting:
                raise RuntimeError(f"Cycle detected involving plugin '{name}'.")

            visiting.add(name)

            for dep in self.dependencies[name]:
                if dep not in self.plugins:
                    raise ValueError(f"Plugin '{name}' depends on missing plugin '{dep}'.")
                execute(dep)

            visiting.remove(name)
            executed.add(name)

            self.plugins[name].run()

        for name in self.plugins:
            execute(name)




