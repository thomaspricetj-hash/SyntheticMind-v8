from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
import time
import re


class RewardModel:
    """
    Simple Reward Model (RM) for SyntheticMind.

    Goal:
    - Take (prompt, response, optional self_eval)
    - Produce a scalar reward score in [0, 1] (soft, heuristic)
    - Can be upgraded later to a learned model

    Current heuristics:
    - Base on self_eval["score"] if present
    - Penalize extremely short or extremely long outputs
    - Penalize if self_eval reports many issues
    """

    def __init__(
        self,
        base_weight: float = 0.7,
        length_weight: float = 0.2,
        issue_weight: float = 0.1,
    ) -> None:
        total = base_weight + length_weight + issue_weight
        if total <= 0:
            raise ValueError("RewardModel weights must sum to > 0")

        # Normalize so they always sum to 1.0
        self.base_weight = base_weight / total
        self.length_weight = length_weight / total
        self.issue_weight = issue_weight / total

    def _length_score(self, length: int) -> float:
        if length <= 0:
            return 0.0
        if length < 64:
            return 0.4
        if length < 512:
            return 0.9
        if length < 4096:
            return 0.8
        return 0.5

    def _issue_score(self, issues_count: int) -> float:
        if issues_count <= 0:
            return 1.0
        if issues_count == 1:
            return 0.7
        if issues_count == 2:
            return 0.5
        return 0.3

    def score(
        self,
        prompt: str,
        response: str,
        self_eval: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base_score = 0.5
        issues_count = 0

        if self_eval is not None:
            try:
                base_score = float(self_eval.get("score", 0.5))
            except Exception:
                base_score = 0.5

            issues = self_eval.get("issues") or []
            if isinstance(issues, list):
                issues_count = len(issues)

        base_score = max(0.0, min(1.0, base_score))

        length = len(response or "")
        length_score = self._length_score(length)
        issue_score = self._issue_score(issues_count)

        reward = (
            self.base_weight * base_score
            + self.length_weight * length_score
            + self.issue_weight * issue_score
        )
        reward = max(0.0, min(1.0, reward))

        return {
            "reward": reward,
            "components": {
                "base_score": base_score,
                "length_score": length_score,
                "issue_score": issue_score,
                "issues_count": issues_count,
                "length": length,
            },
        }


class SelfConsistencyEngine:
    """
    Self‑Consistency Sampling (SCS) engine.

    - Generates multiple candidate responses
    - Scores them (optionally via self‑eval)
    - Selects the best one
    - Provides a lightweight .check(...) API for pipelines that
      want to decide whether to repair or re‑generate an answer.
    """

    def __init__(self, default_samples: int = 3, min_length_for_ok: int = 120) -> None:
        self.default_samples = max(1, int(default_samples))
        self.min_length_for_ok = max(0, int(min_length_for_ok))

    def generate_and_select(
        self,
        prompt: str,
        run_fn: Callable[[str], Dict[str, Any]],
        eval_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
        samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        n = max(1, int(samples or self.default_samples))
        candidates: List[Dict[str, Any]] = []

        for _ in range(n):
            start = time.time()
            raw = run_fn(prompt) or {}
            text = raw.get("text", "") or ""
            eval_data: Optional[Dict[str, Any]] = None

            if eval_fn is not None:
                try:
                    eval_data = eval_fn(prompt, text)
                    if isinstance(eval_data, dict):
                        raw.setdefault("self_eval", eval_data)
                except Exception:
                    eval_data = None

            raw["_scs_latency_ms"] = int((time.time() - start) * 1000)
            candidates.append(raw)

        if not candidates:
            return {"text": "[scs error: no candidates generated]"}

        if eval_fn is None:
            best = candidates[0]
            best["_scs_selected"] = True
            best["_scs_samples"] = n
            return best

        def score_of(c: Dict[str, Any]) -> float:
            se = c.get("self_eval") or {}
            try:
                return float(se.get("score", 0.0))
            except Exception:
                return 0.0

        best = max(candidates, key=score_of)
        best["_scs_selected"] = True
        best["_scs_samples"] = n
        best["_scs_scores"] = [score_of(c) for c in candidates]

        return best


from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import time
import re


# ============================================================
# 3D STRUCTURES
# ============================================================

@dataclass
class Reward3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


@dataclass
class SCS3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


@dataclass
class SelfEval3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


@dataclass
class RQ3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# REWARD MODEL
# ============================================================

class RewardModel:
    """
    Simple Reward Model (RM) for SyntheticMind.

    Goal:
    - Take (prompt, response, optional self_eval)
    - Produce a scalar reward score in [0, 1] (soft, heuristic)
    - Can be upgraded later to a learned model

    Current heuristics:
    - Base on self_eval["score"] if present
    - Penalize extremely short or extremely long outputs
    - Penalize if self_eval reports many issues
    """

    def __init__(
        self,
        base_weight: float = 0.7,
        length_weight: float = 0.2,
        issue_weight: float = 0.1,
    ) -> None:
        total = base_weight + length_weight + issue_weight
        if total <= 0:
            raise ValueError("RewardModel weights must sum to > 0")

        self.base_weight = base_weight / total
        self.length_weight = length_weight / total
        self.issue_weight = issue_weight / total

        self._last_3d: Optional[Reward3D] = None

    def _length_score(self, length: int) -> float:
        if length <= 0:
            return 0.0
        if length < 64:
            return 0.4
        if length < 512:
            return 0.9
        if length < 4096:
            return 0.8
        return 0.5

    def _issue_score(self, issues_count: int) -> float:
        if issues_count <= 0:
            return 1.0
        if issues_count == 1:
            return 0.7
        if issues_count == 2:
            return 0.5
        return 0.3

    def score(
        self,
        prompt: str,
        response: str,
        self_eval: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        base_score = 0.5
        issues_count = 0

        if self_eval is not None:
            try:
                base_score = float(self_eval.get("score", 0.5))
            except Exception:
                base_score = 0.5

            issues = self_eval.get("issues") or []
            if isinstance(issues, list):
                issues_count = len(issues)

        base_score = max(0.0, min(1.0, base_score))

        length = len(response or "")
        length_score = self._length_score(length)
        issue_score = self._issue_score(issues_count)

        reward = (
            self.base_weight * base_score
            + self.length_weight * length_score
            + self.issue_weight * issue_score
        )
        reward = max(0.0, min(1.0, reward))

        out = {
            "reward": reward,
            "components": {
                "base_score": base_score,
                "length_score": length_score,
                "issue_score": issue_score,
                "issues_count": issues_count,
                "length": length,
            },
        }

        self._last_3d = Reward3D(
            axis_x="score",
            axis_y=[f"len:{length}", f"issues:{issues_count}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "reward": reward,
            },
        )

        return out


# ============================================================
# SELF‑CONSISTENCY ENGINE
# ============================================================

class SelfConsistencyEngine:
    """
    Self‑Consistency Sampling (SCS) engine.

    - Generates multiple candidate responses
    - Scores them (optionally via self‑eval)
    - Selects the best one
    - Provides a lightweight .check(...) API for pipelines that
      want to decide whether to repair or re‑generate an answer.
    """

    def __init__(self, default_samples: int = 3, min_length_for_ok: int = 120) -> None:
        self.default_samples = max(1, int(default_samples))
        self.min_length_for_ok = max(0, int(min_length_for_ok))
        self._last_3d: Optional[SCS3D] = None

    def generate_and_select(
        self,
        prompt: str,
        run_fn: Callable[[str], Dict[str, Any]],
        eval_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
        samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        n = max(1, int(samples or self.default_samples))
        candidates: List[Dict[str, Any]] = []

        for _ in range(n):
            c_start = time.time()
            raw = run_fn(prompt) or {}
            text = raw.get("text", "") or ""
            eval_data: Optional[Dict[str, Any]] = None

            if eval_fn is not None:
                try:
                    eval_data = eval_fn(prompt, text)
                    if isinstance(eval_data, dict):
                        raw.setdefault("self_eval", eval_data)
                except Exception:
                    eval_data = None

            raw["_scs_latency_ms"] = int((time.time() - c_start) * 1000)
            candidates.append(raw)

        if not candidates:
            self._last_3d = SCS3D(
                axis_x="generate_and_select",
                axis_y=["no_candidates"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return {"text": "[scs error: no candidates generated]"}

        if eval_fn is None:
            best = candidates[0]
            best["_scs_selected"] = True
            best["_scs_samples"] = n

            self._last_3d = SCS3D(
                axis_x="generate_and_select",
                axis_y=[f"samples:{n}", "no_eval"],
                axis_z={"latency_ms": int((time.time() - start) * 1000)},
            )
            return best

        def score_of(c: Dict[str, Any]) -> float:
            se = c.get("self_eval") or {}
            try:
                return float(se.get("score", 0.0))
            except Exception:
                return 0.0

        best = max(candidates, key=score_of)
        best["_scs_selected"] = True
        best["_scs_samples"] = n
        best["_scs_scores"] = [score_of(c) for c in candidates]

        self._last_3d = SCS3D(
            axis_x="generate_and_select",
            axis_y=[f"samples:{n}", "with_eval"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "scores": best["_scs_scores"],
            },
        )

        return best

    def check(self, prompt: str, answer: Any) -> bool:
        """
        Return True if the answer looks weak / incomplete and should be repaired.

        Heuristics:
        - If answer is empty -> True
        - If answer is shorter than min_length_for_ok -> True
        - If it matches a known "minimal fallback" pattern -> True
        """
        start = time.time()

        if not isinstance(answer, str):
            result = True
        else:
            stripped = answer.strip()
            if not stripped:
                result = True
            elif len(stripped) < self.min_length_for_ok:
                result = True
            else:
                fallback_snippets = [
                    "I can reason, code, analyze, summarize, and help you explore ideas.",
                ]
                result = any(snippet in stripped for snippet in fallback_snippets)

        self._last_3d = SCS3D(
            axis_x="check",
            axis_y=[f"prompt_len:{len(prompt)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "needs_repair": result,
            },
        )

        return result


# ============================================================
# SELF‑EVALUATION ENGINE
# ============================================================

class SelfEvaluationEngine:
    """
    v8 Self‑Evaluation Engine

    - Scores responses for quality, coherence, hallucination risk, structure
    - Optionally repairs low‑scoring responses
    - Logs evaluations for learning via an optional hook
    """

    def __init__(
        self,
        threshold: float = 0.70,
        log_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.threshold = float(threshold)
        self.log_hook = log_hook

        self._uncertainty_re = re.compile(
            r"\b(maybe|not sure|possibly|I think)\b", re.IGNORECASE
        )
        self._hallucination_re = re.compile(
            r"\b(as everyone knows|it is proven that)\b", re.IGNORECASE
        )

        self._last_3d: Optional[SelfEval3D] = None

    def evaluate(self, prompt: str, response: str) -> Dict[str, Any]:
        start = time.time()

        score = 1.0
        issues: List[str] = []
        flags: Dict[str, bool] = {
            "too_short": False,
            "uncertainty": False,
            "hallucination_risk": False,
            "no_structure": False,
        }

        text = (response or "").strip()

        if len(text) < 20:
            score -= 0.25
            issues.append("Response too short")
            flags["too_short"] = True

        if self._uncertainty_re.search(text):
            score -= 0.15
            issues.append("Uncertainty markers detected")
            flags["uncertainty"] = True

        if self._hallucination_re.search(text):
            score -= 0.20
            issues.append("Hallucination‑risk phrasing")
            flags["hallucination_risk"] = True

        if text.count("\n") < 1:
            score -= 0.10
            issues.append("No structure")
            flags["no_structure"] = True

        score = max(score, 0.0)
        needs_repair = score < self.threshold

        result = {
            "score": score,
            "issues": issues,
            "needs_repair": needs_repair,
            "flags": flags,
        }

        self._last_3d = SelfEval3D(
            axis_x="evaluate",
            axis_y=[f"prompt_len:{len(prompt)}", f"text_len:{len(text)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "score": score,
                "needs_repair": needs_repair,
            },
        )

        if self.log_hook is not None:
            try:
                self.log_hook(
                    {
                        "prompt": prompt,
                        "response": response,
                        "evaluation": result,
                    }
                )
            except Exception:
                pass

        return result

    def repair(self, response: str, issues: List[str]) -> str:
        repaired = response or ""

        if "Response too short" in issues:
            repaired += (
                "\n\nAdditional detail: This expands the explanation for clarity "
                "and provides more concrete guidance."
            )

        if "No structure" in issues:
            repaired = "Here’s a clearer version:\n\n" + repaired

        if "Uncertainty markers detected" in issues:
            repaired = re.sub(
                r"\bI think\b",
                "It is likely that",
                repaired,
                flags=re.IGNORECASE,
            )

        self._last_3d = SelfEval3D(
            axis_x="repair",
            axis_y=[f"issues:{len(issues)}"],
            axis_z={"output_len": len(repaired)},
        )

        return repaired


# ============================================================
# RESPONSE QUALITY CONTROLLER
# ============================================================

class ResponseQualityController:
    """
    Thin orchestration layer that wires SCS + SelfEval + RewardModel
    into a single call for the runtime.
    """

    def __init__(
        self,
        scs: Optional[SelfConsistencyEngine] = None,
        self_eval: Optional[SelfEvaluationEngine] = None,
        reward_model: Optional[RewardModel] = None,
    ) -> None:
        self.scs = scs or SelfConsistencyEngine()
        self.self_eval = self_eval or SelfEvaluationEngine()
        self.reward_model = reward_model or RewardModel()
        self._last_3d: Optional[RQ3D] = None

    def run(
        self,
        prompt: str,
        run_fn: Callable[[str], Dict[str, Any]],
        samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        def eval_wrapper(p: str, text: str) -> Dict[str, Any]:
            return self.self_eval.evaluate(p, text)

        best = self.scs.generate_and_select(
            prompt=prompt,
            run_fn=run_fn,
            eval_fn=eval_wrapper,
            samples=samples,
        )

        text = best.get("text", "") or ""
        se = best.get("self_eval") or self.self_eval.evaluate(prompt, text)

        reward = self.reward_model.score(prompt, text, se)
        best["reward"] = reward

        if se.get("needs_repair"):
            repaired = self.self_eval.repair(text, se.get("issues", []))
            best["repaired_text"] = repaired

        self._last_3d = RQ3D(
            axis_x="run",
            axis_y=[f"prompt_len:{len(prompt)}"],
            axis_z={
                "latency_ms": int((time.time() - start) * 1000),
                "score": se.get("score", 0.0),
                "reward": reward.get("reward", 0.0),
                "needs_repair": se.get("needs_repair", False),
            },
        )

        return best
