# syntheticmind/tools/tool_registry.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import traceback

from .python_tool import PythonTool
from .file_tool import FileTool

# NEW BUILTIN TOOLS
from .builtin.calculator import calculator_tool
from .builtin.physics_tool import physics_tool
from .builtin.python_exec import python_exec_tool


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Registry3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# TOOL REGISTRY — MAX REGISTRY + 3D‑MAX
# ============================================================

class ToolRegistry:
    """
    Central registry of all available tools (3D‑MAX Edition).

    Improvements:
        • dynamic registration
        • safe lookup
        • structured envelopes
        • metadata with timestamps + categories
        • built‑in tool wiring
        • future‑proof for evolving tool ecosystem
        • safer error handling
        • introspection snapshot
        • 3D‑MAX telemetry
    """

    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._last_3d: Optional[Registry3D] = None

        # --------------------------------------------------------
        # REGISTER BUILT-IN CLASS-BASED TOOLS
        # --------------------------------------------------------
        self.register("python", PythonTool(), category="core")
        self.register("file", FileTool(), category="core")

        # --------------------------------------------------------
        # REGISTER BUILT-IN FUNCTION TOOLS
        # --------------------------------------------------------
        self.register("calculator", calculator_tool, category="math")
        self.register("physics", physics_tool, category="physics")
        self.register("python_exec", python_exec_tool, category="internal")

    # ------------------------------------------------------------
    # REGISTER TOOL
    # ------------------------------------------------------------
    def register(self, name: str, tool: Any, category: str = "general"):
        """
        Register a tool with metadata.
        """

        self.tools[name] = tool
        self.metadata[name] = {
            "registered_at": time.time(),
            "type": tool.__class__.__name__ if hasattr(tool, "__class__") else "function",
            "category": category,
        }

        self._last_3d = Registry3D(
            axis_x="register",
            axis_y=[f"name:{name}", f"category:{category}"],
            axis_z={"ok": True},
        )

    # ------------------------------------------------------------
    # SAFE LOOKUP
    # ------------------------------------------------------------
    def get(self, name: str) -> Optional[Any]:
        """
        Safe lookup with structured envelope.
        """

        tool = self.tools.get(name)

        self._last_3d = Registry3D(
            axis_x="get",
            axis_y=[f"name:{name}"],
            axis_z={"found": tool is not None},
        )

        return tool

    # ------------------------------------------------------------
    # INTROSPECTION
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Structured snapshot of all registered tools.
        """

        try:
            snap = {
                "ok": True,
                "count": len(self.tools),
                "tools": {
                    name: {
                        "type": meta["type"],
                        "category": meta.get("category", "general"),
                        "registered_at": meta["registered_at"],
                    }
                    for name, meta in self.metadata.items()
                },
                "error": None,
            }

            self._last_3d = Registry3D(
                axis_x="snapshot",
                axis_y=[f"count:{len(self.tools)}"],
                axis_z={"ok": True},
            )

            return snap

        except Exception as e:
            self._last_3d = Registry3D(
                axis_x="snapshot",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            )

            return {
                "ok": False,
                "count": len(self.tools),
                "tools": {},
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

