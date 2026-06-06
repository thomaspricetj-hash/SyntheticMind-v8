# syntheticmind/tools/agent.py

from __future__ import annotations
from typing import Dict, Any
import time
import traceback

from .tool_registry import ToolRegistry


class Agent:
    """
    Command interpreter + tool dispatcher.

    Supports:
        • python execution
        • file read/write
        • future tool types
        • structured envelopes
        • safe execution
    """

    def __init__(self):
        self.registry = ToolRegistry()

    # ------------------------------------------------------------
    # INTERNAL: SAFE TOOL LOOKUP
    # ------------------------------------------------------------
    def _get_tool(self, name: str):
        tool = self.registry.get(name)
        if not tool:
            raise ValueError(f"unknown tool: {name}")
        return tool

    # ------------------------------------------------------------
    # INTERNAL: EXECUTE PYTHON
    # ------------------------------------------------------------
    def _run_python(self, code: str) -> Dict[str, Any]:
        tool = self._get_tool("python")
        return tool.run(code)

    # ------------------------------------------------------------
    # INTERNAL: READ FILE
    # ------------------------------------------------------------
    def _run_read(self, path: str) -> Dict[str, Any]:
        tool = self._get_tool("file")
        return tool.read(path)

    # ------------------------------------------------------------
    # INTERNAL: WRITE FILE
    # ------------------------------------------------------------
    def _run_write(self, path: str, content: str) -> Dict[str, Any]:
        tool = self._get_tool("file")
        return tool.write(path, content)

    # ------------------------------------------------------------
    # MAIN ENTRYPOINT
    # ------------------------------------------------------------
    def run(self, command: str) -> Dict[str, Any]:
        """
        Expected formats:
            python: <code>
            read: <path>
            write: <path>|<content>

        Returns a structured envelope:
            {
                "ok": bool,
                "latency_ms": int,
                "command": str,
                "result": Any,
                "error": None
            }
        """

        start = time.time()

        try:
            command = command.strip()

            # ----------------------------------------------------
            # PYTHON EXECUTION
            # ----------------------------------------------------
            if command.startswith("python:"):
                code = command[len("python:"):].strip()
                result = self._run_python(code)
                return {
                    "ok": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "command": command,
                    "result": result,
                    "error": None,
                }

            # ----------------------------------------------------
            # READ FILE
            # ----------------------------------------------------
            if command.startswith("read:"):
                path = command[len("read:"):].strip()
                result = self._run_read(path)
                return {
                    "ok": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "command": command,
                    "result": result,
                    "error": None,
                }

            # ----------------------------------------------------
            # WRITE FILE
            # ----------------------------------------------------
            if command.startswith("write:"):
                rest = command[len("write:"):].strip()
                if "|" not in rest:
                    raise ValueError("write requires path|content")

                path, content = rest.split("|", 1)
                result = self._run_write(path.strip(), content)
                return {
                    "ok": True,
                    "latency_ms": int((time.time() - start) * 1000),
                    "command": command,
                    "result": result,
                    "error": None,
                }

            # ----------------------------------------------------
            # UNKNOWN COMMAND
            # ----------------------------------------------------
            raise ValueError(f"unknown command: {command}")

        except Exception as e:
            return {
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "command": command,
                "result": None,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
