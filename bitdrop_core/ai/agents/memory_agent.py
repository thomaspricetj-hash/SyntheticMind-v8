# ai/agents/memory_agent.py

from __future__ import annotations
from .base import Agent


class MemoryAgent(Agent):
    """
    Handles memory operations:
        • write
        • recall
        • search
        • inspect
    """

    name = "memory"
    description = "Reads, writes, and retrieves memory."
    capabilities = {
        "write": True,
        "recall": True,
        "search": True,
        "inspect": True,
    }

    # ------------------------------------------------------------
    # PUBLIC CONVENIENCE METHODS (optional)
    # ------------------------------------------------------------
    def write(self, text: str):
        """Direct write without agent envelope."""
        self.runtime.memory.remember(text)

    def recall(self, query: str, k: int = 3):
        """Direct recall without agent envelope."""
        return self.runtime.memory.recall(query, top_k=k)

    # ------------------------------------------------------------
    # INTERNAL EXECUTION
    # ------------------------------------------------------------
    def _run(self, action: str, **kwargs):
        """
        Core memory logic.
        This method is wrapped by Agent.run() for:
            • tracing
            • timing
            • error handling
            • pre/post hooks

        Supported actions:
            • write(text=str)
            • recall(query=str, k=int)
            • search(query=str)
            • inspect()
        """

        mem = self.runtime.memory

        # -----------------------------
        # WRITE
        # -----------------------------
        if action == "write":
            text = kwargs.get("text")
            if not text:
                return {"error": "Missing 'text' for write()"}
            mem.remember(text)
            return {"action": "write", "text": text}

        # -----------------------------
        # RECALL
        # -----------------------------
        if action == "recall":
            query = kwargs.get("query")
            k = kwargs.get("k", 3)
            if not query:
                return {"error": "Missing 'query' for recall()"}
            results = mem.recall(query, top_k=k)
            return {"action": "recall", "query": query, "results": results}

        # -----------------------------
        # SEARCH (semantic or raw)
        # -----------------------------
        if action == "search":
            query = kwargs.get("query")
            if not query:
                return {"error": "Missing 'query' for search()"}
            if hasattr(mem, "search"):
                results = mem.search(query)
            else:
                results = mem.recall(query, top_k=5)
            return {"action": "search", "query": query, "results": results}

        # -----------------------------
        # INSPECT (debug)
        # -----------------------------
        if action == "inspect":
            if hasattr(mem, "inspect"):
                return {"action": "inspect", "items": mem.inspect()}
            return {"error": "Memory backend does not support inspect()"}

        # -----------------------------
        # UNKNOWN ACTION
        # -----------------------------
        return {"error": f"Unknown memory action: {action}"}

    # ------------------------------------------------------------
    # OPTIONAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        # Could attach metadata or log memory access
        pass

    def _post_run(self, result, success: bool):
        # Log memory writes into episodic memory
        if success and isinstance(result, dict) and result.get("action") == "write":
            self.runtime.memory.remember(f"[memory-agent] wrote: {result.get('text')}")

