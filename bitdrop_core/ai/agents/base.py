# ai/agents/base.py

from __future__ import annotations
import time
import uuid
from typing import Any, Dict


class Agent:
    """
    Base class for all agents in the MetaModelRuntime.

    Features:
        • standardized metadata
        • safe execution wrapper
        • pre/post hooks
        • tracing + timing
        • capability declaration
        • runtime-aware context
    """

    # Static metadata
    name: str = "base-agent"
    description: str = "Base agent"
    capabilities: Dict[str, Any] = {}

    def __init__(self, runtime: "MetaModelRuntime"):
        self.runtime = runtime

    # ------------------------------------------------------------
    # PUBLIC ENTRYPOINT
    # ------------------------------------------------------------
    def run(self, *args, **kwargs) -> Any:
        """
        Safe execution wrapper around _run().
        Handles:
            • tracing
            • timing
            • error capture
            • pre/post hooks
        """

        trace_id = str(uuid.uuid4())
        start = time.time()

        self._pre_run(args, kwargs)

        try:
            result = self._run(*args, **kwargs)
            success = True
        except Exception as e:
            result = {"error": str(e)}
            success = False

        self._post_run(result, success)

        return {
            "agent": self.name,
            "trace_id": trace_id,
            "latency_ms": int((time.time() - start) * 1000),
            "success": success,
            "result": result,
        }

    # ------------------------------------------------------------
    # INTERNAL HOOKS
    # ------------------------------------------------------------
    def _pre_run(self, args, kwargs):
        """Hook for subclasses to override."""
        pass

    def _post_run(self, result, success: bool):
        """Hook for subclasses to override."""
        pass

    # ------------------------------------------------------------
    # ABSTRACT METHOD
    # ------------------------------------------------------------
    def _run(self, *args, **kwargs) -> Any:
        """
        Subclasses must implement this.
        This method should NOT handle errors or tracing.
        """
        raise NotImplementedError(f"{self.name} does not implement _run()")

