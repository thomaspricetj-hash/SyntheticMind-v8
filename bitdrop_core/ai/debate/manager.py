# ai/debate/manager.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time

from .round import DebateRound
from .scorer import DebateScorer


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Debate3D:
    """
    3D structural view of a debate run.

    axis_x: high-level operation ("run_debate")
    axis_y: structural decomposition (rounds, allow_rebuttals)
    axis_z: metadata (latency, question_len, total_args, final_confidence)
    """
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ============================================================
# DEBATE MANAGER (3D‑MAX)
# ============================================================

class DebateManager:
    """
    Coordinates multi‑agent debate and consensus formation.
    Supports:
        • multi‑round debates
        • agent‑role weighting
        • rebuttal chaining
        • scoring + consensus
        • safe agent execution
        • structured logging
    Now 3D‑MAX introspectable.
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.scorer = DebateScorer()

        self.role_weights = {
            "planner": 1.2,
            "executor": 1.0,
            "critic": 1.4,
            "memory": 0.8,
            "tool": 1.0,
        }

        self._last_3d: Optional[Debate3D] = None

    # ------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------
    def run_debate(
        self,
        question: str,
        rounds: int = 1,
        allow_rebuttals: bool = True
    ) -> Dict[str, Any]:
        """
        Run a multi‑round debate and return:
            • all rounds
            • scored arguments
            • consensus
        """

        start = time.time()

        all_rounds: List[Dict[str, Any]] = []
        last_round: Optional[DebateRound] = None

        for r in range(rounds):
            round_obj = DebateRound(question, round_index=r)

            # AGENT ARGUMENT COLLECTION
            for agent_name, agent in self.runtime.agents.items():
                if agent_name not in self.role_weights:
                    continue  # skip non‑debate agents

                try:
                    response = self._run_agent(agent, question)
                except Exception as e:
                    response = f"[error: {e}]"

                rebuttal_to = None
                if allow_rebuttals and last_round:
                    rebuttal_to = self._choose_rebuttal_target(last_round)

                round_obj.add_argument(
                    agent_name,
                    str(response),
                    rebuttal_to=rebuttal_to,
                    metadata={"round": r}
                )

            # SCORING
            round_data = round_obj.to_dict()
            scored = self._apply_role_weights(self.scorer.score(round_data))

            consensus = scored[0] if scored else None

            all_rounds.append({
                "round": round_data,
                "scored": scored,
                "consensus": consensus,
            })

            last_round = round_obj

        # FINAL CONSENSUS ACROSS ROUNDS
        final_consensus = self._final_consensus(all_rounds)

        latency_ms = int((time.time() - start) * 1000)
        total_args = sum(len(r["scored"]) for r in all_rounds)
        final_conf = (
            float(final_consensus.get("confidence", 0.0))
            if final_consensus
            else 0.0
        )

        self._last_3d = Debate3D(
            axis_x="run_debate",
            axis_y=[
                f"rounds:{rounds}",
                f"allow_rebuttals:{allow_rebuttals}",
                f"total_args:{total_args}",
            ],
            axis_z={
                "latency_ms": latency_ms,
                "question_len": len(question),
                "final_confidence": final_conf,
                "has_consensus": final_consensus is not None,
            },
        )

        return {
            "question": question,
            "rounds": all_rounds,
            "final_consensus": final_consensus,
        }

    # ------------------------------------------------------------
    # INTERNAL UTILITIES
    # ------------------------------------------------------------
    def _run_agent(self, agent, question: str):
        """Safe agent execution with signature flexibility."""
        try:
            return agent.run(question=question)
        except TypeError:
            return agent.run(question)

    def _choose_rebuttal_target(self, last_round: DebateRound) -> Optional[int]:
        """Pick a target argument to rebut (simple heuristic: rebut the strongest)."""
        if not last_round.arguments:
            return None
        return len(last_round.arguments) - 1  # rebut last argument

    def _apply_role_weights(self, scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Multiply scores by agent role weights."""
        for entry in scored:
            agent = entry["agent"]
            weight = self.role_weights.get(agent, 1.0)
            entry["score"] *= weight
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    def _final_consensus(self, all_rounds: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Pick the best argument across all rounds."""
        all_args: List[Dict[str, Any]] = []
        for r in all_rounds:
            all_args.extend(r["scored"])

        if not all_args:
            return None

        all_args.sort(key=lambda x: x["score"], reverse=True)
        best = all_args[0]

        scores = [a["score"] for a in all_args]
        if len(scores) > 1:
            spread = max(scores) - min(scores)
            confidence = 1.0 - (spread / (max(scores) + 1e-6))
        else:
            confidence = 1.0

        best["confidence"] = float(confidence)
        return best

