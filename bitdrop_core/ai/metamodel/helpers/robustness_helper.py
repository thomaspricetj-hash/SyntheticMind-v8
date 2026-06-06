from __future__ import annotations
from typing import Dict, Any
import re


class RobustnessHelperV4:
    """
    RobustnessHelperV4 — high‑reliability output evaluator.

    Responsibilities:
      • Detect contradictions
      • Detect logical inconsistencies
      • Detect hallucination-like drift
      • Detect adversarial patterns
      • Detect incomplete or malformed answers
      • Detect overconfident wrongness
      • Detect repetition loops
      • Provide a structured robustness score + flags

    This helper does NOT generate text. It evaluates the model's output
    and returns a structured robustness profile.
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
        Returns a structured robustness profile.
        """

        t = answer.lower()

        # --- 1. Nonsense / drift detection ---
        nonsense = bool(self.NONSENSE_RE.search(t))

        # --- 2. Repetition loop detection ---
        repetition = bool(self.REPETITION_RE.search(answer))

        # --- 3. Overconfidence detection ---
        overconfident = bool(self.OVERCONFIDENT_RE.search(t))

        # --- 4. Contradiction detection ---
        contradiction = bool(self.CONTRADICTION_RE.search(t))

        # --- 5. Adversarial detection ---
        adversarial = bool(self.ADVERSARIAL_RE.search(query.lower()))

        # --- 6. Incomplete answer detection ---
        incomplete = self._detect_incomplete(answer)

        # --- 7. Logical consistency score ---
        logic_score = self._logic_score(
            nonsense=nonsense,
            repetition=repetition,
            contradiction=contradiction,
            incomplete=incomplete,
        )

        # --- 8. Build robustness profile ---
        return {
            "nonsense": nonsense,
            "repetition": repetition,
            "overconfident": overconfident,
            "contradiction": contradiction,
            "adversarial_prompt": adversarial,
            "incomplete": incomplete,
            "logic_score": logic_score,
            "robust": logic_score >= 0.75,
        }

    # ------------------------------------------------------------
    # Incomplete answer detection
    # ------------------------------------------------------------
    def _detect_incomplete(self, answer: str) -> bool:
        """
        Detects if the answer ends abruptly or is missing expected structure.
        """

        if not answer:
            return True

        # Ends mid‑sentence
        if answer.strip().endswith(("and", "or", "but", ",")):
            return True

        # Very short answers to complex questions
        if len(answer.split()) < 5:
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
