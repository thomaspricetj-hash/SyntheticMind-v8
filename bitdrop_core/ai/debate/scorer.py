# ai/debate/scorer.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import math


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class DebateScore3D:
    """
    3D structural view of a scoring pass.

    axis_x: high-level operation ("score")
    axis_y: structural decomposition (arg_count, prompt_present)
    axis_z: metadata (avg_len, avg_depth, avg_relevance, avg_evidence)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# DEBATE SCORER (3D‑MAX)
# ============================================================

class DebateScorer:
    """
    Multi‑feature scoring engine for debate arguments.
    Evaluates:
        • depth
        • clarity
        • structure
        • relevance
        • evidence density
        • novelty
        • length (minor factor)
    Now 3D‑MAX introspectable.
    """

    def __init__(self) -> None:
        self._last_3d: Optional[DebateScore3D] = None

    def score(self, round_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        arguments = round_data.get("arguments", [])
        prompt = round_data.get("prompt", "")

        scored: List[Dict[str, Any]] = []
        seen_contents = set()

        depths: List[float] = []
        relevances: List[float] = []
        evidences: List[float] = []
        lengths: List[int] = []

        for arg in arguments:
            content = arg.get("content", "")
            agent = arg.get("agent", "unknown")

            length = len(content)
            sentences = content.count(".") + content.count("!") + content.count("?")
            commas = content.count(",")
            paragraphs = content.count("\n")

            depth = sentences * 2 + paragraphs * 3 + commas * 0.5
            clarity = max(0, 50 - (length / 20))
            relevance = self._keyword_overlap(prompt, content)
            evidence = (
                content.count("because") * 2 +
                content.count("for example") * 3 +
                sum(c.isdigit() for c in content) * 0.5
            )
            novelty = 10 if content not in seen_contents else -10
            seen_contents.add(content)
            hallucination_penalty = -15 if "as an ai" in content.lower() else 0

            score = (
                depth * 1.5 +
                clarity * 1.2 +
                relevance * 2.0 +
                evidence * 1.8 +
                novelty +
                hallucination_penalty +
                math.log(length + 1)
            )

            depths.append(depth)
            relevances.append(relevance)
            evidences.append(evidence)
            lengths.append(length)

            scored.append({
                "agent": agent,
                "content": content,
                "score": float(score),
                "features": {
                    "depth": depth,
                    "clarity": clarity,
                    "relevance": relevance,
                    "evidence": evidence,
                    "novelty": novelty,
                    "hallucination_penalty": hallucination_penalty,
                    "length": length,
                }
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        arg_count = len(arguments)
        avg_len = sum(lengths) / arg_count if arg_count else 0.0
        avg_depth = sum(depths) / arg_count if arg_count else 0.0
        avg_rel = sum(relevances) / arg_count if arg_count else 0.0
        avg_evid = sum(evidences) / arg_count if arg_count else 0.0

        self._last_3d = DebateScore3D(
            axis_x="score",
            axis_y=[
                f"args:{arg_count}",
                f"prompt_present:{bool(prompt)}",
            ],
            axis_z={
                "avg_length": float(avg_len),
                "avg_depth": float(avg_depth),
                "avg_relevance": float(avg_rel),
                "avg_evidence": float(avg_evid),
            },
        )

        return scored

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------

    def _keyword_overlap(self, prompt: str, content: str) -> float:
        """Simple keyword relevance scoring."""
        if not prompt:
            return 0.0

        pwords = {w.lower() for w in prompt.split() if len(w) > 3}
        cwords = {w.lower() for w in content.split() if len(w) > 3}

        if not pwords:
            return 0.0

        overlap = pwords.intersection(cwords)
        return len(overlap) / len(pwords) * 10.0

