# ai/debate/scorer.py

from __future__ import annotations
from typing import Dict, Any, List
import math


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
    """

    def score(self, round_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        arguments = round_data.get("arguments", [])
        prompt = round_data.get("prompt", "")

        scored = []
        seen_contents = set()

        for arg in arguments:
            content = arg.get("content", "")
            agent = arg.get("agent", "unknown")

            # ------------------------------------------------------------
            # FEATURE EXTRACTION
            # ------------------------------------------------------------

            length = len(content)
            sentences = content.count(".") + content.count("!") + content.count("?")
            commas = content.count(",")
            paragraphs = content.count("\n")

            # Depth: more sentences & structure → deeper reasoning
            depth = sentences * 2 + paragraphs * 3 + commas * 0.5

            # Clarity: penalize rambling or extremely long sentences
            clarity = max(0, 50 - (length / 20))

            # Relevance: overlap with prompt keywords
            relevance = self._keyword_overlap(prompt, content)

            # Evidence: presence of numbers, citations, examples
            evidence = (
                content.count("because") * 2 +
                content.count("for example") * 3 +
                sum(c.isdigit() for c in content) * 0.5
            )

            # Novelty: penalize repeated arguments
            novelty = 10 if content not in seen_contents else -10
            seen_contents.add(content)

            # Hallucination penalty: crude but effective
            hallucination_penalty = (
                -15 if "as an AI" in content.lower() else 0
            )

            # ------------------------------------------------------------
            # FINAL SCORE
            # ------------------------------------------------------------

            score = (
                depth * 1.5 +
                clarity * 1.2 +
                relevance * 2.0 +
                evidence * 1.8 +
                novelty +
                hallucination_penalty +
                math.log(length + 1)  # small length bonus
            )

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

        # Sort descending by score
        scored.sort(key=lambda x: x["score"], reverse=True)
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

