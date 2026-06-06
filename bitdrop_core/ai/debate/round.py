# ai/debate/round.py

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional


class DebateRound:
    """
    Represents a single multi‑agent debate round with:
        • question / prompt
        • chronological arguments
        • timestamps
        • rebuttal linking
        • scoring metadata
        • agent ordering
    """

    def __init__(self, question: str, round_index: int = 0):
        self.question = question
        self.round_index = round_index
        self.created_at = time.time()

        # Each argument:
        # {
        #   "agent": str,
        #   "content": str,
        #   "timestamp": float,
        #   "rebuttal_to": Optional[int],
        #   "metadata": {...}
        # }
        self.arguments: List[Dict[str, Any]] = []

    # ------------------------------------------------------------
    # ADD ARGUMENTS
    # ------------------------------------------------------------

    def add_argument(
        self,
        agent_name: str,
        content: str,
        rebuttal_to: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add an argument to the round.
        rebuttal_to: index of argument being rebutted (optional)
        metadata: scoring hints, agent role, etc.
        """

        entry = {
            "agent": agent_name,
            "content": content,
            "timestamp": time.time(),
            "rebuttal_to": rebuttal_to,
            "metadata": metadata or {},
        }

        self.arguments.append(entry)
        return entry

    # ------------------------------------------------------------
    # QUERY UTILITIES
    # ------------------------------------------------------------

    def last_argument(self) -> Optional[Dict[str, Any]]:
        """Return the most recent argument."""
        return self.arguments[-1] if self.arguments else None

    def arguments_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        """Return all arguments from a specific agent."""
        return [a for a in self.arguments if a["agent"] == agent_name]

    def rebuttals_of(self, index: int) -> List[Dict[str, Any]]:
        """Return all arguments that rebut a specific argument."""
        return [a for a in self.arguments if a["rebuttal_to"] == index]

    # ------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Full structured representation for scoring or logging."""
        return {
            "question": self.question,
            "round_index": self.round_index,
            "created_at": self.created_at,
            "arguments": self.arguments,
        }

    def summary(self) -> str:
        """Human‑readable summary for debugging or logs."""
        lines = [f"Round {self.round_index}: {self.question}"]
        for i, arg in enumerate(self.arguments):
            agent = arg["agent"]
            content = arg["content"]
            rebut = f" (rebuttal to #{arg['rebuttal_to']})" if arg["rebuttal_to"] is not None else ""
            lines.append(f"  #{i} [{agent}]{rebut}: {content}")
        return "\n".join(lines)
