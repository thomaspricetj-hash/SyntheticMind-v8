from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import re


@dataclass
class Robustness3D:
    """
    3D structural view of robustness evaluation.

    axis_x: raw answer text
    axis_y: line-wise decomposition
    axis_z: robustness signals + scores
    """
    raw_answer: str
    axis_x: str
    axis_y: list[str]
    axis_z: Dict[str, Any]


class RobustnessHelperV4:
    """
    RobustnessHelperV4 — high‑reliability output evaluator (3D-aware).

    Responsibilities:
      • Detect contradictions
      • Detect logical inconsistencies
      • Detect hallucination-like drift
      • Detect adversarial patterns
      • Detect incomplete or malformed answers
      • Detect overconfident wrongness
      • Detect repetition loops
      • Provide a structured robustness score + flags
      • Provide a 3D structural view of robustness signals
    """

    # Patterns for detecting nonsense or drift
    NONSENSE_RE = re.compile(
        r"(?:asdf|qwer|lorem ipsum|random string|nonsense|gibberish|###|@@@)",
        re.IGNORECASE
    )

    # Patterns for detecting repetition loops
    REPETITION_RE = re.compile(r"(.+)\1{2,}", re.DOTALL)

    # Patterns for detecting overconfidence
    OVERCONFIDENT_RE = re.compile(
        r"\b(guaranteed|certainly|absolutely|no doubt|100% sure)\b",
        re.IGNORECASE
    )

    # Patterns for detecting contradictions
    CONTRADICTION_RE = re.compile(
        r"\b(but that contradicts|however that conflicts|this is inconsistent)\b",
        re.IGNORECASE
    )

    # Patterns for detecting adversarial prompts
    ADVERSARIAL_RE = re.compile(
        r"(ignore previous instructions|bypass|override safety|jailbreak)",
        re.IGNORECASE
    )

    def analyze(self, query: str, answer: str) -> Dict[str, Any]:
        """
        Returns a structured robustness profile + 3D structure.
        """

        t = (answer or "").lower()

        # --- 1. Nonsense / drift detection ---
        nonsense = bool(self.NONSENSE_RE.search(t))

        # --- 2. Repetition loop detection ---
        repetition = bool(self.REPETITION_RE.search(answer or ""))

        # --- 3. Overconfidence detection ---
        overconfident = bool(self.OVERCONFIDENT_RE.search(t))

        # --- 4. Contradiction detection ---
        contradiction = bool(self.CONTRADICTION_RE.search(t))

        # --- 5. Adversarial detection ---
        adversarial = bool(self.ADVERSARIAL_RE.search((query or "").lower()))

        # --- 6. Incomplete answer detection ---
        incomplete = self._detect_incomplete(answer or "")

        # --- 7. Logical consistency score ---
        logic_score = self._logic_score(
            nonsense=nonsense,
            repetition=repetition,
            contradiction=contradiction,
            incomplete=incomplete,
        )

        robust = logic_score >= 0.75

        # --- 8. Build robustness profile ---
        profile = {
            "nonsense": nonsense,
            "repetition": repetition,
            "overconfident": overconfident,
            "contradiction": contradiction,
            "adversarial_prompt": adversarial,
            "incomplete": incomplete,
            "logic_score": logic_score,
            "robust": robust,
        }

        # --- 9. 3D structural view ---
        structure_3d = self._build_3d(answer or "", profile)

        profile["structure_3d"] = structure_3d
        return profile

    # ------------------------------------------------------------
    # Incomplete answer detection
    # ------------------------------------------------------------
    def _detect_incomplete(self, answer: str) -> bool:
        """
        Detects if the answer ends abruptly or is missing expected structure.
        """

        if not answer:
            return True

        stripped = answer.strip()

        # Ends mid‑sentence
        if stripped.endswith(("and", "or", "but", ",")):
            return True

        # Very short answers to complex questions
        if len(stripped.split()) < 5:
            return True

        return False

    # ------------------------------------------------------------
    # Logic score computation
    # ------------------------------------------------------------
    def _logic_score(
        self,
        *,
        nonsense: bool,
        repetition: bool,
        contradiction: bool,
        incomplete: bool,
    ) -> float:
        """
        Computes a 0.0–1.0 logic score.
        """

        score = 1.0

        if nonsense:
            score -= 0.5
        if repetition:
            score -= 0.3
        if contradiction:
            score -= 0.4
        if incomplete:
            score -= 0.2

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------
    # 3D builder
    # ------------------------------------------------------------
    def _build_3d(self, answer: str, profile: Dict[str, Any]) -> Robustness3D:
        lines = (answer or "").splitlines()
        axis_z = dict(profile)
        axis_z.pop("structure_3d", None)
        return Robustness3D(
            raw_answer=answer or "",
            axis_x=answer or "",
            axis_y=lines,
            axis_z=axis_z,
        )

