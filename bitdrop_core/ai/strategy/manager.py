# syntheticmind/strategy/strategy_manager.py

from __future__ import annotations
from typing import Dict, Any, List
import time
import traceback

from .analyzer import StrategyAnalyzer
from .tree import StrategyTreeBuilder


class StrategyManager:
    """
    High-level strategic planner that integrates:
        • planner agent
        • simulation engine
        • debate engine
        • world model
        • strategy analyzer
        • decision tree builder
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.analyzer = StrategyAnalyzer()
        self.tree_builder = StrategyTreeBuilder()

    # ------------------------------------------------------------
    # INTERNAL: DRAFT PLAN
    # ------------------------------------------------------------
    def _draft_linear_plan(self, goal_text: str) -> List[str]:
        """
        Ask the planner agent for a rough multi-step plan.
        Fallback: single-step plan.
        """

        try:
            planner_agent = self.runtime.agents.get("planner")
            if planner_agent:
                resp = planner_agent.run(question=goal_text)

                # Structured planner output
                if isinstance(resp, dict) and "steps" in resp:
                    return [str(x) for x in resp["steps"]]

                # Raw list
                if isinstance(resp, list):
                    return [str(x) for x in resp]

                # Single string
                return [str(resp)]

        except Exception:
            pass

        # Fallback
        return [f"Work toward: {goal_text}"]

    # ------------------------------------------------------------
    # INTERNAL: RISK ESTIMATION
    # ------------------------------------------------------------
    def _estimate_risk(self, steps: List[str]) -> float:
        """
        Crude risk estimate based on step count and keywords.
        """

        base = min(1.0, len(steps) * 0.1)

        if any("deploy" in s.lower() or "production" in s.lower() for s in steps):
            base += 0.2

        return min(1.0, base)

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT: PLAN FOR GOAL
    # ------------------------------------------------------------
    def plan_for_goal(self, goal_text: str) -> Dict[str, Any]:
        """
        Build a strategic plan for a given goal.
        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "goal": str,
                "plan": {...},
                "simulation": {...},
                "debate": {...},
                "world": {...},
                "analysis": {...},
                "tree": {...},
                "error": None
            }
        """

        start = time.time()

        try:
            # ----------------------------------------------------
            # 1) DRAFT PLAN
            # ----------------------------------------------------
            steps = self._draft_linear_plan(goal_text)
            risk = self._estimate_risk(steps)

            candidate_plan = {
                "goal": goal_text,
                "steps": steps,
                "risk": risk,
            }

            # ----------------------------------------------------
            # 2) SIMULATION
            # ----------------------------------------------------
            sim_steps = [
                {"text": s, "intent": "small_reasoning", "metadata": {}}
                for s in steps
            ]

            sim_result = self.runtime.simulation.simulate_plan(sim_steps)

            # ----------------------------------------------------
            # 3) DEBATE
            # ----------------------------------------------------
            debate_result = self.runtime.debate.run_debate(goal_text)

            # ----------------------------------------------------
            # 4) WORLD MODEL PROPAGATION
            # ----------------------------------------------------
            main_entity = goal_text.split(" ")[0] if goal_text else ""
            world_prop = (
                self.runtime.world.sim.simulate_propagation(main_entity)
                if main_entity
                else {}
            )

            # ----------------------------------------------------
            # 5) ANALYSIS
            # ----------------------------------------------------
            analysis = self.analyzer.analyze([candidate_plan])

            # ----------------------------------------------------
            # 6) DECISION TREE
            # ----------------------------------------------------
            tree = self.tree_builder.build_tree(steps)

            # ----------------------------------------------------
            # FINAL STRUCTURED ENVELOPE
            # ----------------------------------------------------
            return {
                "ok": True,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": goal_text,
                "plan": candidate_plan,
                "simulation": sim_result,
                "debate": debate_result,
                "world": world_prop,
                "analysis": analysis,
                "tree": tree,
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "goal": goal_text,
                "plan": None,
                "simulation": None,
                "debate": None,
                "world": None,
                "analysis": None,
                "tree": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    # ------------------------------------------------------------
    # PLAN FOR EXISTING GOAL
    # ------------------------------------------------------------
    def plan_for_existing_goal(self, goal_id: str) -> Dict[str, Any]:
        goal = self.runtime.goals.get(goal_id)
        if not goal:
            return {
                "ok": False,
                "error": f"unknown goal id: {goal_id}",
                "goal_id": goal_id,
            }
        return self.plan_for_goal(goal.text)

