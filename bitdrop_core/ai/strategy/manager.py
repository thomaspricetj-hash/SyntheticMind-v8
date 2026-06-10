from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import time
import traceback

from .analyzer import StrategyAnalyzer
from .tree import StrategyTreeBuilder


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class StrategyManager3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# STRATEGY MANAGER — MAX SPEED + 3D‑MAX
# ============================================================

class StrategyManager:
    """
    High‑level strategic planner integrating:
        • planner agent
        • simulation engine
        • debate engine
        • world model
        • strategy analyzer
        • decision tree builder
        • benchmark‑compatible solve()
        • 3D‑MAX telemetry
    """

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime
        self.analyzer = StrategyAnalyzer()
        self.tree_builder = StrategyTreeBuilder()
        self._last_3d: Optional[StrategyManager3D] = None

    # ------------------------------------------------------------
    # INTERNAL: DRAFT PLAN
    # ------------------------------------------------------------
    def _draft_linear_plan(self, goal_text: str) -> List[str]:
        try:
            planner_agent = self.runtime.agents.get("planner")
            if planner_agent:
                resp = planner_agent.run(question=goal_text)

                if isinstance(resp, dict) and "steps" in resp:
                    return [str(x) for x in resp["steps"]]

                if isinstance(resp, list):
                    return [str(x) for x in resp]

                return [str(resp)]
        except Exception:
            pass

        return [f"Work toward: {goal_text}"]

    # ------------------------------------------------------------
    # INTERNAL: RISK ESTIMATION
    # ------------------------------------------------------------
    def _estimate_risk(self, steps: List[str]) -> float:
        base = min(1.0, len(steps) * 0.1)
        if any("deploy" in s.lower() or "production" in s.lower() for s in steps):
            base += 0.2
        return min(1.0, base)

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT: PLAN FOR GOAL
    # ------------------------------------------------------------
    def plan_for_goal(self, goal_text: str) -> Dict[str, Any]:
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
                if main_entity else {}
            )

            # ----------------------------------------------------
            # 5) ANALYSIS
            # ----------------------------------------------------
            analysis = self.analyzer.analyze([candidate_plan])

            # ----------------------------------------------------
            # 6) DECISION TREE
            # ----------------------------------------------------
            tree = self.tree_builder.build_tree(steps)

            latency = int((time.time() - start) * 1000)

            # ----------------------------------------------------
            # 3D‑MAX TELEMETRY
            # ----------------------------------------------------
            self._last_3d = StrategyManager3D(
                axis_x="plan_for_goal",
                axis_y=[f"steps:{len(steps)}", f"risk:{risk}"],
                axis_z={
                    "latency_ms": latency,
                    "sim_ok": sim_result.get("ok", True),
                    "debate_ok": debate_result.get("ok", True),
                    "analysis_ok": analysis.get("ok", True),
                },
            )

            return {
                "ok": True,
                "latency_ms": latency,
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
            latency = int((time.time() - start) * 1000)

            self._last_3d = StrategyManager3D(
                axis_x="plan_for_goal",
                axis_y=["exception"],
                axis_z={"latency_ms": latency, "error": str(e)},
            )

            return {
                "ok": False,
                "latency_ms": latency,
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
            self._last_3d = StrategyManager3D(
                axis_x="plan_for_existing_goal",
                axis_y=[f"goal_id:{goal_id}"],
                axis_z={"ok": False, "reason": "unknown_goal"},
            )
            return {
                "ok": False,
                "error": f"unknown goal id: {goal_id}",
                "goal_id": goal_id,
            }

        return self.plan_for_goal(goal.text)

    # ------------------------------------------------------------
    # BENCHMARK‑COMPATIBLE SOLVE()
    # ------------------------------------------------------------
    def solve(self, text: str) -> str:
        try:
            steps = self._draft_linear_plan(text)
            if steps:
                self._last_3d = StrategyManager3D(
                    axis_x="solve",
                    axis_y=[f"steps:{len(steps)}"],
                    axis_z={"ok": True},
                )
                return f"Recommended first step: {steps[0]}"

            self._last_3d = StrategyManager3D(
                axis_x="solve",
                axis_y=["fallback"],
                axis_z={"ok": True},
            )
            return "Break the problem into steps and execute them in order."

        except Exception:
            self._last_3d = StrategyManager3D(
                axis_x="solve",
                axis_y=["exception"],
                axis_z={"ok": False},
            )
            return "Divide the task into steps and proceed methodically."


