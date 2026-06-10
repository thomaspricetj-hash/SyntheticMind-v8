from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import re


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------
@dataclass
class Summarization3D:
    """
    3D structural view of summarization intent analysis.

    axis_x: raw text
    axis_y: line-by-line decomposition
    axis_z: extracted constraints + triggers
    """
    raw_text: str
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# SUMMARIZATION HELPER (3D-AWARE)
# ------------------------------------------------------------
class SummarizationHelperV1:
    """
    Maximum‑strength summarization intent detector (3D-enabled).
    """

    # Precompiled patterns
    SENTENCE_RE = re.compile(r"in\s+(\d+)\s+sentences?", re.IGNORECASE)
    WORD_RE = re.compile(r"in\s+(\d+)\s+words?", re.IGNORECASE)
    PERCENT_RE = re.compile(r"(?:reduce|compress|shorten)\s+by\s+(\d+)%", re.IGNORECASE)
    LENGTH_HINT_RE = re.compile(
        r"(ultra short|very short|short version|brief|concise|compressed|tiny summary|quick summary)",
        re.IGNORECASE
    )

    # Negative filters
    NEGATIVE_PATTERNS = [
        "summary judgment",
        "summary statistics",
        "summary table",
        "summary report",
        "summary of benefits",
        "executive summary",
        "summary offense",
    ]

    # Primary triggers
    PRIMARY_TRIGGERS = [
        "summarize",
        "summary",
        "tl;dr",
        "in short",
        "short version",
        "brief version",
        "make this shorter",
        "shorten this",
        "condense this",
        "compress this",
        "what's the gist",
        "what is the gist",
        "main idea",
        "explain simply",
        "explain this simply",
        "give me the gist",
        "give me the short version",
        "boil this down",
        "reduce this",
        "simplify this",
        "simplify the text",
        "eli5",
        "explain like i'm 5",
        "core points",
        "key points",
        "main points",
        "essentials only",
        "short explanation",
        "short answer",
    ]

    # ------------------------------------------------------------
    # 3D builder
    # ------------------------------------------------------------
    def _build_3d(self, text: str, result: Dict[str, Any]) -> Summarization3D:
        lines = (text or "").splitlines()
        axis_z = dict(result)
        return Summarization3D(
            raw_text=text or "",
            axis_x=text or "",
            axis_y=lines,
            axis_z=axis_z,
        )

    # ------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------
    def analyze(self, text: str) -> dict:
        t = text.lower()

        # --- 1. Negative-case filtering ---
        for neg in self.NEGATIVE_PATTERNS:
            if neg in t:
                result = {
                    "detected": False,
                    "sentences": None,
                    "words": None,
                    "percent": None,
                    "length_hint": None,
                }
                result["structure_3d"] = self._build_3d(text, result)
                return result

        # --- 2. Summarization intent detection ---
        detected = any(trigger in t for trigger in self.PRIMARY_TRIGGERS)

        if not detected:
            if any(phrase in t for phrase in ["key points", "main points", "core points"]):
                detected = True

        # --- 3. Extract constraints ---
        sentences = None
        words = None
        percent = None
        length_hint = None

        m = self.SENTENCE_RE.search(text)
        if m:
            sentences = int(m.group(1))

        m = self.WORD_RE.search(text)
        if m:
            words = int(m.group(1))

        m = self.PERCENT_RE.search(text)
        if m:
            percent = int(m.group(1))

        m = self.LENGTH_HINT_RE.search(text)
        if m:
            length_hint = m.group(1).lower()

        # --- 4. Fallback length hints ---
        if not length_hint:
            if "very concise" in t:
                length_hint = "very short"
            elif "super short" in t:
                length_hint = "ultra short"
            elif "short summary" in t:
                length_hint = "short"
            elif "quick summary" in t:
                length_hint = "brief"

        # --- 5. Build result ---
        result = {
            "detected": detected,
            "sentences": sentences,
            "words": words,
            "percent": percent,
            "length_hint": length_hint,
        }

        # --- 6. Attach 3D structure ---
        result["structure_3d"] = self._build_3d(text, result)

        return result





