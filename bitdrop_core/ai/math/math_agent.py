from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import math

from .math_engine import MathEngine, memory as math_memory
from .detectors import looks_like_math
from .semantic_math import embed_math_text


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class MathAgent3D:
    """
    3D structural view of a math-agent solve operation.

    axis_x: raw problem text
    axis_y: structural decomposition (tokens, lines)
    axis_z: metadata (safety, fiction, reuse score, symbolic result)
    """
    raw_problem: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# INTERNAL: cosine similarity
# ------------------------------------------------------------
def _cosine(u, v) -> float:
    if not u or not v or len(u) != len(v):
        return 0.0
    num = sum(a * b for a, b in zip(u, v))
    den1 = math.sqrt(sum(a * a for a in u))
    den2 = math.sqrt(sum(b * b for b in v))
    if den1 == 0 or den2 == 0:
        return 0.0
    return num / (den1 * den2)


# ------------------------------------------------------------
# MAIN AGENT (3D-AWARE)
# ------------------------------------------------------------
class MathAgent:
    """
    MathAgent V5 — Safety‑Hardened + Hallucination‑Protected + 3D‑Aware

    Improvements:
      - Rejects dangerous prompts
      - Rejects fictional / impossible entities
      - Tightened math intent detection
      - Prevents unsafe fallback behavior
      - Uses deterministic symbolic engine + local reuse memory
      - Provides 3D structural metadata for orchestrator routing
    """

    def __init__(self, engine: MathEngine):
        self.engine = engine
        self.memory = math_memory  # shared math memory log

    # ------------------------------------------------------------
    # 3D builder
    # ------------------------------------------------------------
    def _build_3d(
        self,
        problem: str,
        *,
        is_dangerous: bool,
        is_fictional: bool,
        is_math: bool,
        reuse_score: float,
        reused_answer: Optional[str],
        symbolic_answer: Optional[str],
    ) -> MathAgent3D:

        lines = (problem or "").splitlines()
        tokens = (problem or "").split()

        axis_z = {
            "is_dangerous": is_dangerous,
            "is_fictional": is_fictional,
            "is_math": is_math,
            "reuse_score": reuse_score,
            "reused_answer": reused_answer,
            "symbolic_answer": symbolic_answer,
            "tokens": tokens,
            "char_count": len(problem or ""),
        }

        return MathAgent3D(
            raw_problem=problem or "",
            axis_x=problem or "",
            axis_y=lines,
            axis_z=axis_z,
        )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def solve(self, problem: str) -> str:
        problem = problem.strip()

        # Safety
        is_dangerous = self._is_dangerous(problem)
        if is_dangerous:
            self._last_3d = self._build_3d(
                problem,
                is_dangerous=True,
                is_fictional=False,
                is_math=False,
                reuse_score=0.0,
                reused_answer=None,
                symbolic_answer=None,
            )
            return "[MathAgent] I cannot assist with harmful or dangerous requests."

        # Fiction
        is_fictional = self._is_fictional(problem)
        if is_fictional:
            self._last_3d = self._build_3d(
                problem,
                is_dangerous=False,
                is_fictional=True,
                is_math=False,
                reuse_score=0.0,
                reused_answer=None,
                symbolic_answer=None,
            )
            return "[MathAgent] This entity or event does not exist."

        # Math intent
        is_math = self._is_math(problem)
        if not is_math:
            self._last_3d = self._build_3d(
                problem,
                is_dangerous=False,
                is_fictional=False,
                is_math=False,
                reuse_score=0.0,
                reused_answer=None,
                symbolic_answer=None,
            )
            return f"[MathAgent] Not a math problem: {problem}"

        # Try reuse
        reused, reuse_score = self._try_reuse(problem)
        if reused:
            self._last_3d = self._build_3d(
                problem,
                is_dangerous=False,
                is_fictional=False,
                is_math=True,
                reuse_score=reuse_score,
                reused_answer=reused,
                symbolic_answer=None,
            )
            return reused

        # Try symbolic
        symbolic = self._try_symbolic(problem)
        if symbolic:
            self._store(problem, symbolic)
            self._last_3d = self._build_3d(
                problem,
                is_dangerous=False,
                is_fictional=False,
                is_math=True,
                reuse_score=reuse_score,
                reused_answer=None,
                symbolic_answer=symbolic,
            )
            return symbolic

        # No LLM fallback allowed
        self._last_3d = self._build_3d(
            problem,
            is_dangerous=False,
            is_fictional=False,
            is_math=True,
            reuse_score=reuse_score,
            reused_answer=None,
            symbolic_answer=None,
        )
        return "[MathAgent] Unable to solve with the current symbolic engine."

    # ------------------------------------------------------------
    # Safety / Hallucination Detection
    # ------------------------------------------------------------
    def _is_dangerous(self, text: str) -> bool:
        danger_terms = [
            "weapon", "bomb", "explosive", "harm", "kill",
            "dangerous", "attack", "poison", "build a gun",
            "make a weapon", "instructions to harm",
        ]
        t = text.lower()
        return any(term in t for term in danger_terms)

    def _is_fictional(self, text: str) -> bool:
        t = text.lower()
        fictional_markers = [
            "interstellar", "galactic", "time travel",
            "2031 interstellar chess league",
            "parallel universe", "mythical",
        ]
        return any(term in t for term in fictional_markers)

    # ------------------------------------------------------------
    # Math Intent Detection (tightened)
    # ------------------------------------------------------------
    def _is_math(self, text: str) -> bool:
        if looks_like_math(text):
            return True

        math_tokens = ["solve", "derivative", "integral", "equation", "compute"]
        if any(tok in text.lower() for tok in math_tokens):
            return True

        return False

    # ------------------------------------------------------------
    # Semantic Reuse (local memory)
    # ------------------------------------------------------------
    def _try_reuse(self, problem: str) -> tuple[Optional[str], float]:
        emb = embed_math_text(problem)
        best_score = 0.0
        best_answer: Optional[str] = None

        for item in self.memory.items:
            if item.embedding is None:
                continue
            if item.tags.get("namespace") != "math":
                continue
            score = _cosine(emb, item.embedding)
            if score > best_score:
                best_score = score
                best_answer = item.tags.get("answer")

        if best_answer is not None and best_score >= 0.92:
            return best_answer, best_score

        return None, best_score

    # ------------------------------------------------------------
    # Symbolic solving
    # ------------------------------------------------------------
    def _try_symbolic(self, problem: str) -> Optional[str]:
        try:
            result = self.engine.analyze(problem)
            if result and "error" not in result.lower():
                return result
        except Exception:
            pass
        return None

    # ------------------------------------------------------------
    # Memory write
    # ------------------------------------------------------------
    def _store(self, problem: str, answer: str) -> None:
        try:
            emb = embed_math_text(problem)
            self.memory.write(
                content=problem,
                tags={"answer": answer, "namespace": "math"},
                embedding=emb,
            )
        except Exception:
            pass




