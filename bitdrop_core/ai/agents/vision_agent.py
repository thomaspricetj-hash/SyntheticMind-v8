# ai/agents/vision_agent.py

from __future__ import annotations
from .base import Agent


class VisionAgent(Agent):
    """
    Handles multimodal reasoning:
        • image description
        • visual question answering
        • multimodal embeddings
        • structured visual analysis
    """

    name = "vision"
    description = "Analyzes images and answers visual questions."
    capabilities = {
        "vision": True,
        "image_description": True,
        "visual_qa": True,
        "multimodal_reasoning": True,
    }

    # ------------------------------------------------------------
    # PUBLIC CONVENIENCE METHODS (optional)
    # ------------------------------------------------------------
    def describe(self, image_bytes: bytes):
        """Direct call without agent envelope."""
        return self.runtime.vision.describe(image_bytes)

    def ask(self, question: str, image_bytes: bytes):
        """Direct call without agent envelope."""
        return self.runtime.vision.ask(question, image_bytes)

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, action: str, **kwargs):
        """
        Core multimodal logic.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks

        Supported actions:
            • describe(image_bytes=...)
            • ask(question=..., image_bytes=...)
            • embed(image_bytes=...)
        """

        vision = getattr(self.runtime, "vision", None)
        if vision is None:
            return {"error": "Vision subsystem unavailable"}

        # -----------------------------
        # DESCRIBE
        # -----------------------------
        if action == "describe":
            img = kwargs.get("image_bytes")
            if not img:
                return {"error": "Missing 'image_bytes' for describe()"}
            desc = vision.describe(img)
            return {"action": "describe", "description": desc}

        # -----------------------------
        # VISUAL QUESTION ANSWERING
        # -----------------------------
        if action == "ask":
            q = kwargs.get("question")
            img = kwargs.get("image_bytes")
            if not q or not img:
                return {"error": "Missing 'question' or 'image_bytes' for ask()"}
            ans = vision.ask(q, img)
            return {"action": "ask", "question": q, "answer": ans}

        # -----------------------------
        # EMBEDDINGS
        # -----------------------------
        if action == "embed":
            img = kwargs.get("image_bytes")
            if not img:
                return {"error": "Missing 'image_bytes' for embed()"}
            if not hasattr(vision, "embed"):
                return {"error": "Vision backend does not support embeddings"}
            emb = vision.embed(img)
            return {"action": "embed", "embedding": emb}

        # -----------------------------
        # UNKNOWN ACTION
        # -----------------------------
        return {"error": f"Unknown vision action: {action}"}

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could attach multimodal metadata or warm up GPU
        pass

    def _post_run(self, result, success: bool):
        # Log visual reasoning events
        if success and isinstance(result, dict) and result.get("action"):
            self.runtime.memory.remember(
                f"[vision-agent] performed {result['action']} operation"
            )

