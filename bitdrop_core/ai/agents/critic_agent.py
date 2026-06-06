# ai/agents/critic_agent.py

from __future__ import annotations
from .base import Agent


class CriticAgent(Agent):
    """
    Evaluates outputs and identifies issues using the runtime's refiner.
    """

    name = "critic"
    description = "Evaluates and critiques outputs."
    capabilities = {
        "critique": True,
        "analysis": True,
        "safety_checks": True,
    }

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, prompt: str, output: str):
        """
        Core critic logic.
        Uses the runtime's refiner.critic.critique() method.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks
        """

        critic = getattr(self.runtime.refiner, "critic", None)
        if critic is None or not hasattr(critic, "critique"):
            return {
                "error": "Critic subsystem unavailable",
                "prompt": prompt,
                "output": output,
            }

        # Perform critique
        critique = critic.critique(prompt, output)

        return {
            "prompt": prompt,
            "output": output,
            "critique": critique,
        }

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could log, warm up critic, or attach metadata
        pass

    def _post_run(self, result, success: bool):
        # Could store critique in memory or metrics
        if success and isinstance(result, dict) and "critique" in result:
            self.runtime.memory.remember(
                f"[critic] critique generated for prompt '{result.get('prompt')}'"
            )
