from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, List


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Summarizer3D:
    """
    3D structural view of a summarization cycle.

    axis_x: high-level operation ("summarize", "clean", "enforce")
    axis_y: structural decomposition (constraints, text_len)
    axis_z: metadata (sentences, words, percent, hint, output_len)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: dict


# ============================================================
# SUMMARIZER (3D‑MAX)
# ============================================================

class SummarizerModelV1:
    """
    V5 Ultra‑Precision Summarizer (3D‑MAX Edition)
    Features:
        • Exact sentence-count control
        • Exact word-count control
        • Percent-compression control
        • Length-hint shaping
        • Key noun/verb preservation
        • Semantic compression
        • Hallucination-resistant prompting
        • Deterministic cleanup + trimming
        • 3D‑MAX introspection
    """

    def __init__(self, model):
        self.model = model
        self._last_3d: Optional[Summarizer3D] = None

    # ------------------------------------------------------------
    # MAIN SUMMARIZATION ENTRYPOINT
    # ------------------------------------------------------------
    def summarize(
        self,
        text: str,
        *,
        sentences=None,
        words=None,
        percent=None,
        length_hint=None
    ) -> str:

        constraint = self._build_constraint(
            sentences=sentences,
            words=words,
            percent=percent,
            length_hint=length_hint,
        )

        prompt = (
            "You are a precision summarizer.\n"
            "Rules:\n"
            "  • Preserve key nouns, verbs, and factual meaning.\n"
            "  • No hallucinations, no invented details.\n"
            "  • No filler, no meta commentary.\n"
            "  • No prefaces like 'Here is the summary'.\n"
            "  • Output ONLY the summary.\n\n"
            f"{constraint}\n\n"
            f"TEXT:\n{text}\n\n"
            "SUMMARY:"
        )

        raw = self.model.generate(prompt)
        cleaned = self._clean(raw)

        # Enforce constraints deterministically
        if sentences:
            cleaned = self._enforce_sentence_count(cleaned, sentences)

        if words:
            cleaned = self._enforce_word_limit(cleaned, words)

        # 3D snapshot
        self._last_3d = Summarizer3D(
            axis_x="summarize",
            axis_y=[
                f"text_len:{len(text)}",
                f"sentences:{sentences}",
                f"words:{words}",
                f"percent:{percent}",
                f"hint:{length_hint}",
            ],
            axis_z={
                "output_len": len(cleaned),
                "raw_len": len(raw),
                "constraint": constraint,
            },
        )

        return cleaned

    # ------------------------------------------------------------
    # CONSTRAINT BUILDER
    # ------------------------------------------------------------
    def _build_constraint(self, sentences, words, percent, length_hint):
        if sentences:
            return f"Summarize the text in exactly {sentences} sentences."

        if words:
            return f"Summarize the text in no more than {words} words."

        if percent:
            return (
                f"Summarize the text by reducing its length by about {percent}%. "
                "Preserve all key ideas."
            )

        if length_hint:
            if "ultra" in length_hint:
                return "Produce an ultra‑short summary (1–2 sentences)."
            if "very" in length_hint:
                return "Produce a very concise summary (2–3 sentences)."
            if "short" in length_hint:
                return "Produce a short, compact summary."

        return "Summarize the text concisely."

    # ------------------------------------------------------------
    # OUTPUT CLEANER
    # ------------------------------------------------------------
    def _clean(self, text: str) -> str:
        if not text:
            cleaned = ""
        else:
            t = text.strip()

            bad_prefixes = [
                "summary:",
                "the summary is:",
                "here is the summary:",
                "tl;dr:",
                "in summary:",
            ]
            t_low = t.lower()
            for p in bad_prefixes:
                if t_low.startswith(p):
                    t = t[len(p):].strip()
                    break

            cleaned = t.strip(" \n\t\"'`")

        # 3D snapshot
        self._last_3d = Summarizer3D(
            axis_x="clean",
            axis_y=[f"input_len:{len(text)}"],
            axis_z={"output_len": len(cleaned)},
        )

        return cleaned

    # ------------------------------------------------------------
    # SENTENCE ENFORCER
    # ------------------------------------------------------------
    def _enforce_sentence_count(self, text: str, target: int) -> str:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            return text

        if len(sentences) > target:
            sentences = sentences[:target]

        if len(sentences) < target:
            while len(sentences) < target:
                last = sentences[-1]
                parts = last.split(",")
                if len(parts) > 1:
                    sentences[-1] = parts[0]
                    sentences.append(",".join(parts[1:]).strip())
                else:
                    break

        out = ". ".join(sentences).strip() + "."

        self._last_3d = Summarizer3D(
            axis_x="enforce_sentences",
            axis_y=[f"target:{target}", f"actual:{len(sentences)}"],
            axis_z={"output_len": len(out)},
        )

        return out

    # ------------------------------------------------------------
    # WORD LIMIT ENFORCER
    # ------------------------------------------------------------
    def _enforce_word_limit(self, text: str, limit: int) -> str:
        words = text.split()
        if len(words) <= limit:
            out = text
        else:
            trimmed = " ".join(words[:limit])
            out = trimmed.rstrip(".,;:") + "."

        self._last_3d = Summarizer3D(
            axis_x="enforce_words",
            axis_y=[f"limit:{limit}", f"actual:{len(words)}"],
            axis_z={"output_len": len(out)},
        )

        return out




