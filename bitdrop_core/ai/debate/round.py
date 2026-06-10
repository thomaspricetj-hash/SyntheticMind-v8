from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class DebateRound3D:
    """
    3D structural view of a debate round operation.

    axis_x: high-level operation ("init", "add_argument", "serialize")
    axis_y: structural decomposition (round_index, arg_count)
    axis_z: metadata (question_len, timestamps, agent list)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# DEBATE ROUND (3D‑MAX)
# ============================================================

class DebateRound:
    """
    Represents a single multi‑agent debate round with:
        • question / prompt
        • chronological arguments
        • timestamps
        • rebuttal linking
        • scoring metadata
        • agent ordering
    Now 3D‑MAX introspectable.
    """

    def __init__(self, question: str, round_index: int = 0):
        self.question = question
        self.round_index = round_index
        self.created_at = time.time()
        self.arguments: List[Dict[str, Any]] = []
        self._last_3d: Optional[DebateRound3D] = None

        # 3D snapshot for initialization
        self._last_3d = DebateRound3D(
            axis_x="init",
            axis_y=[f"round:{round_index}", "args:0"],
            axis_z={
                "question_len": len(question),
                "created_at": self.created_at,
            },
        )

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

        # 3D snapshot for argument addition
        self._last_3d = DebateRound3D(
            axis_x="add_argument",
            axis_y=[
                f"round:{self.round_index}",
                f"args:{len(self.arguments)}",
                f"agent:{agent_name}",
            ],
            axis_z={
                "content_len": len(content),
                "rebuttal_to": rebuttal_to,
                "metadata_keys": list((metadata or {}).keys()),
            },
        )

        return entry

    # ------------------------------------------------------------
    # QUERY UTILITIES
    # ------------------------------------------------------------

    def last_argument(self) -> Optional[Dict[str, Any]]:
        return self.arguments[-1] if self.arguments else None

    def arguments_by_agent(self, agent_name: str) -> List[Dict[str, Any]]:
        return [a for a in self.arguments if a["agent"] == agent_name]

    def rebuttals_of(self, index: int) -> List[Dict[str, Any]]:
        return [a for a in self.arguments if a["rebuttal_to"] == index]

    # ------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Full structured representation for scoring or logging."""

        out = {
            "question": self.question,
            "round_index": self.round_index,
            "created_at": self.created_at,
            "arguments": self.arguments,
        }

        # 3D snapshot for serialization
        self._last_3d = DebateRound3D(
            axis_x="serialize",
            axis_y=[
                f"round:{self.round_index}",
                f"args:{len(self.arguments)}",
            ],
            axis_z={
                "question_len": len(self.question),
                "agent_list": [a["agent"] for a in self.arguments],
            },
        )

        return out

    def summary(self) -> str:
        """Human‑readable summary for debugging or logs."""
        lines = [f"Round {self.round_index}: {self.question}"]
        for i, arg in enumerate(self.arguments):
            agent = arg["agent"]
            content = arg["content"]
            rebut = (
                f" (rebuttal to #{arg['rebuttal_to']})"
                if arg["rebuttal_to"] is not None
                else ""
            )
            lines.append(f"  #{i} [{agent}]{rebut}: {content}")
        return "\n".join(lines)

