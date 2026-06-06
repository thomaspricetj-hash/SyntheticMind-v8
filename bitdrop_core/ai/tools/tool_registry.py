# syntheticmind/tools/tool_registry.py

from __future__ import annotations
from typing import Dict, Any, Optional
import time
import traceback

from .python_tool import PythonTool
from .file_tool import FileTool


class ToolRegistry:
    """
    Central registry of all available tools.

    Features:
        • dynamic registration
        • safe lookup
        • structured envelopes
        • metadata
        • future-proof for evolving tool ecosystem
    """

    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

        # Register built-in tools
        self.register("python", PythonTool())
        self.register("file", FileTool())

    # ------------------------------------------------------------
    # REGISTER TOOL
    # ------------------------------------------------------------
    def register(self, name: str, tool: Any):
        """
        Register a tool with metadata.
        """

        self.tools[name] = tool
        self.metadata[name] = {
            "registered_at": time.time(),
            "type": tool.__class__.__name__,
        }

    # ------------------------------------------------------------
    # SAFE LOOKUP
    # ------------------------------------------------------------
    def get(self, name: str) -> Optional[Any]:
        """
        Safe lookup with structured envelope.
        """

        return self.tools.get(name)

    # ------------------------------------------------------------
    # INTROSPECTION
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of all registered tools.
        """

        try:
            return {
                "ok": True,
                "count": len(self.tools),
                "tools": {
                    name: {
                        "type": meta["type"],
                        "registered_at": meta["registered_at"],
                    }
                    for name, meta in self.metadata.items()
                },
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "count": len(self.tools),
                "tools": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
